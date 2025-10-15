from pyrekordbox import Rekordbox6Database
from sqlalchemy import desc
from datetime import datetime
import os
import time
import json

def get_current_playing_track():
    """
    Queries which song was most recently played in Rekordb    print("Starting monitoring...")
    print("Press Ctrl+C to stop.")
    print("="*50)    Searches for the song with the most recent 'created_at' timestamp across all history entries.
    
    Returns:
        dict: Current song information or None if not found
    """
    try:
        # Connect to Rekordbox database
        db = Rekordbox6Database()
        
        # Get the most recent history entries (last 5)
        history_query = db.get_history()
        history_model = history_query.column_descriptions[0]['type']
        recent_histories = history_query.order_by(desc(history_model.DateCreated)).limit(5).all()
        
        if not recent_histories:
            return None
        
        # Find the song with the most recent timestamp among all entries
        most_recent_song = None
        most_recent_time = None
        source_history = None
        
        for history in recent_histories:
            if history.Songs:
                for song in history.Songs:
                    # Use created_at or updated_at to find the most recent
                    song_time = song.updated_at if song.updated_at else song.created_at
                    
                    if song_time and (most_recent_time is None or song_time > most_recent_time):
                        most_recent_song = song
                        most_recent_time = song_time
                        source_history = history
        
        if not most_recent_song:
            return None
            
        # Get song details
        content = db.get_content().filter_by(ID=most_recent_song.ContentID).first()
        
        if not content:
            return None
            
        # Extract artist information
        artist_name = "Unknown"
        if content.Artist and hasattr(content.Artist, 'Name'):
            artist_name = content.Artist.Name
        elif content.Artist:
            artist_name = str(content.Artist)
        
        # Extract album information
        album_name = "Unknown Album"
        if content.Album and hasattr(content.Album, 'Name'):
            album_name = content.Album.Name
        elif content.Album:
            album_name = str(content.Album)
        
        # Extract genre information
        genre_name = "Unknown Genre"
        if content.Genre and hasattr(content.Genre, 'Name'):
            genre_name = content.Genre.Name
        elif content.Genre:
            genre_name = str(content.Genre)
            
        return {
            'title': content.Title or "Unknown Title",
            'artist': artist_name,
            'album': album_name,
            'genre': genre_name, 
            'file_path': content.FolderPath or "Unknown Path",
            'last_played': most_recent_time,
            'history_name': source_history.Name,
            'track_number': most_recent_song.TrackNo
        }
        
    except Exception as e:
        print(f"Error updating music history: {e}")
        return None

def write_current_track_to_file(output_dir="obs_output"):
    """
    Writes current song information to files for OBS use
    
    Args:
        output_dir: Directory where files will be saved
    """
    try:
        # Create directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        track_info = get_current_playing_track()
        
        if track_info:
            # Format: "Artist - Title"
            artist_title = f"{track_info['artist']} - {track_info['title']}"
            
            # Update history of last 15 songs
            update_music_history(track_info, output_dir)
            
            # Files for different OBS needs
            files_to_write = {
                'current_track.txt': artist_title,
                'artist.txt': track_info['artist'],
                'title.txt': track_info['title'],
                'album.txt': track_info['album'],
                'full_info.txt': f"""{track_info['title']}
 {track_info['artist']}
 {track_info['album']}
 {track_info['last_played'].strftime('%H:%M:%S')}""",
                'track_info.json': json.dumps(track_info, default=str, ensure_ascii=False, indent=2)
            }
            
            # Write all files
            for filename, content in files_to_write.items():
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            print(f"Files updated in '{output_dir}':")
            print(f"   current_track.txt: {artist_title}")
            print(f"   artist.txt: {track_info['artist']}")
            print(f"   title.txt: {track_info['title']}")
            print(f"   full_info.txt: Complete information")
            print(f"   track_info.json: JSON data")
            print(f"   history.txt: History of last 15 songs")
            
            return True
        else:
            # Write empty files if no song
            empty_files = ['current_track.txt', 'artist.txt', 'title.txt', 'album.txt']
            for filename in empty_files:
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("No song playing")
            
            print("No song detected - files cleared")
            return False
            
    except Exception as e:
        print(f"Error writing files: {e}")
        return False

def update_music_history(track_info, output_dir="obs_output", max_history=15):
    """
    Updates the history file with the latest songs
    
    Args:
        track_info: Current song information
        output_dir: Directory where to save
        max_history: Maximum number of songs in history
    """
    try:
        history_file = os.path.join(output_dir, 'history.txt')
        history_json_file = os.path.join(output_dir, 'history.json')
        
        # Load existing history
        history = []
        if os.path.exists(history_json_file):
            try:
                with open(history_json_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []
        
        # Create entry for current song
        current_entry = {
            'artist': track_info['artist'],
            'title': track_info['title'],
            'album': track_info['album'],
            'played_at': track_info['last_played'].strftime('%H:%M:%S'),
            'played_date': track_info['last_played'].strftime('%Y-%m-%d'),
            'track_number': track_info['track_number']
        }
        
        # Check if song is not already the last in history (avoid duplicates)
        if not history or (history[0]['artist'] != current_entry['artist'] or 
                          history[0]['title'] != current_entry['title']):
            
            # Add at the beginning of the list
            history.insert(0, current_entry)
            
            # Limit to maximum number
            history = history[:max_history]
            
            # Save history in JSON
            with open(history_json_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            # Create formatted text file for OBS
            with open(history_file, 'w', encoding='utf-8') as f:
                f.write("MUSIC HISTORY (Last 15)\n")
                f.write("=" * 50 + "\n\n")
                
                for i, track in enumerate(history, 1):
                    if i == 1:
                        f.write(f"{i:2d}. {track['artist']} - {track['title']} CURRENT\n")
                    else:
                        f.write(f"   {i:2d}. {track['artist']} - {track['title']}\n")
                    f.write(f"       Album: {track['album']} | Last Played: {track['played_at']}\n\n")
            
            # Create simple version for OBS (just song list)
            simple_history_file = os.path.join(output_dir, 'history_simple.txt')
            with open(simple_history_file, 'w', encoding='utf-8') as f:
                for i, track in enumerate(history, 1):
                    prefix = "🎶 " if i == 1 else "   "
                    f.write(f"{prefix}{track['artist']} - {track['title']}\n")
            
            # Create numbered version
            numbered_history_file = os.path.join(output_dir, 'history_numbered.txt')
            with open(numbered_history_file, 'w', encoding='utf-8') as f:
                for i, track in enumerate(history, 1):
                    marker = " (Current)" if i == 1 else ""
                    f.write(f"{i:2d}. {track['artist']} - {track['title']}{marker}\n")
    
    except Exception as e:
        print(f"Error updating history: {e}")

def monitor_and_update(output_dir="obs_output", interval=10):
    """
    Continuously monitors and updates files when the song changes
    
    Args:
        output_dir: Directory where files will be saved
        interval: Interval in seconds to check for changes
    """
    print(f"Starting continuous monitoring...")
    print(f"Files will be saved in: {os.path.abspath(output_dir)}")
    print(f" Checking every {interval} seconds")
    print("Press Ctrl+C to stop\n")
    
    last_track = None
    
    try:
        while True:
            current_track = get_current_playing_track()
            
            # Check if the song changed
            if current_track:
                current_id = f"{current_track['artist']} - {current_track['title']}"
                
                if current_id != last_track:
                    print(f"New song detected: {current_id}")
                    write_current_track_to_file(output_dir)
                    last_track = current_id
                else:
                    print(f"🔄 Current song: {current_id}")
            else:
                if last_track is not None:
                    print("No song detected")
                    write_current_track_to_file(output_dir)
                    last_track = None
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring interrupted by user")
    except Exception as e:
        print(f"\n Error in monitoring: {e}")

def print_current_track():
    """
    Prints current song information in a formatted way
    """
    track_info = get_current_playing_track()
    
    if track_info:
        print(" CURRENT SONG IN REKORDBOX ")
        print("=" * 50)
        print(f"Title: {track_info['title']}")
        print(f"Artist: {track_info['artist']}")
        print(f"Album: {track_info['album']}")
        print(f"Genre: {track_info['genre']}")
        print(f"Last played: {track_info['last_played']}")
        print(f"History: {track_info['history_name']}")
        print(f"Track #: {track_info['track_number']}")
        print(f"File: {track_info['file_path']}")
        print("=" * 50)
    else:
        print(" Unable to find information about the current song")
        print("Make sure that:")
        print("- Rekordbox is running")
        print("- At least one song has been played")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "monitor":
            # Continuous monitoring mode
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            output_dir = sys.argv[3] if len(sys.argv) > 3 else "obs_output"
            monitor_and_update(output_dir, interval)
            
        elif command == "write":
            # Write once only
            output_dir = sys.argv[2] if len(sys.argv) > 2 else "obs_output"
            write_current_track_to_file(output_dir)
            
        elif command == "show":
            # Show on screen
            print_current_track()
        else:
            print("Available commands:")
            print("  python track.py show          - Shows current song on screen")
            print("  python track.py write [dir]   - Writes files once")
            print("  python track.py monitor [sec] [dir] - Monitors continuously")
            print("\nExamples:")
            print("  python track.py monitor 5 obs_files")
            print("  python track.py write my_obs_folder")
    else:
        # Default behavior: show on screen
        print_current_track()