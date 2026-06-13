import os
import json

with open('track_new.py', 'r') as f:
    content = f.read()

old_write_block = """
            for filename, content in files_to_write.items():
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
"""

new_write_block = """
            for filename, filecontent in files_to_write.items():
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(filecontent)
            
            # Write per-deck output
            decks = get_current_tracks_by_deck(source)
            if decks:
                for deck_id, deck_track in decks.items():
                    deck_dir = os.path.join(output_dir, f"deck_{deck_id}")
                    if not os.path.exists(deck_dir):
                        os.makedirs(deck_dir)
                    
                    deck_artist_title = f"{deck_track['artist']} - {deck_track['title']}"
                    
                    deck_files_to_write = {
                        'current_track.txt': deck_artist_title,
                        'artist.txt': deck_track['artist'],
                        'title.txt': deck_track['title'],
                        'album.txt': deck_track['album']
                    }
                    
                    for filename, filecontent in deck_files_to_write.items():
                        filepath = os.path.join(deck_dir, filename)
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(filecontent)
"""

content = content.replace(old_write_block, new_write_block)

with open('track.py', 'w') as f:
    f.write(content)
