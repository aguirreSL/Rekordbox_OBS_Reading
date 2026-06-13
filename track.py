"""
DJ Track Monitor for OBS Studio Integration.

Monitors DJ software (Rekordbox or Serato DJ Pro) for track changes and
writes current song information to text files for OBS integration.

Usage:
    python track.py show [--source rekordbox|serato|auto]
    python track.py write [dir] [--source rekordbox|serato|auto]
    python track.py monitor [interval] [dir] [--source rekordbox|serato|auto]
"""

from datetime import datetime
import os
import time
import json
import sys
import glob

import rekordbox_reader
import serato_reader


# A track is added to the history only after it has been continuously on a deck
# for this many seconds (i.e. it actually "played"), not the moment it's loaded.
# Matches Rekordbox's "played" threshold. Tune via env var.
HISTORY_PLAYED_SECONDS = int(os.environ.get('HISTORY_PLAYED_SECONDS', '30'))


def get_current_playing_track(source="auto"):
    """
    Gets the currently playing track from the specified DJ software source.
    
    Args:
        source: "rekordbox", "serato", or "auto" (tries both, picks most recent)
    
    Returns:
        dict: Track information or None if not found
    """
    if source == "rekordbox":
        return rekordbox_reader.get_current_playing_track()
    elif source == "serato":
        return serato_reader.get_current_playing_track()
    elif source == "auto":
        return _auto_detect_track()
    else:
        print(f"Unknown source: {source}. Use 'rekordbox', 'serato', or 'auto'.")
        return None


def _auto_detect_track():
    """
    Tries both sources and returns the track with the most recent timestamp.
    Falls back to whichever source returns data.
    
    Returns:
        dict: Track information from the most recently active source, or None
    """
    rekordbox_track = None
    serato_track = None
    
    try:
        rekordbox_track = rekordbox_reader.get_current_playing_track()
    except Exception:
        pass
    
    try:
        serato_track = serato_reader.get_current_playing_track()
    except Exception:
        pass
    
    if rekordbox_track and serato_track:
        # Compare timestamps to pick the most recent
        rb_time = rekordbox_track.get('last_played')
        sr_time = serato_track.get('last_played')
        
        if rb_time and sr_time:
            return rekordbox_track if rb_time > sr_time else serato_track
        elif rb_time:
            return rekordbox_track
        else:
            return serato_track
    
    return rekordbox_track or serato_track



def get_current_tracks_by_deck(source="auto"):
    if source == "rekordbox":
        return rekordbox_reader.get_current_tracks_by_deck()
    elif source == "serato":
        return serato_reader.get_current_tracks_by_deck()
    elif source == "auto":
        rb = None
        sr = None
        try:
            rb = rekordbox_reader.get_current_tracks_by_deck()
        except: pass
        try:
            sr = serato_reader.get_current_tracks_by_deck()
        except: pass
        
        rb_latest = max([t['last_played'] for t in rb.values()]) if rb else None
        sr_latest = max([t['last_played'] for t in sr.values()]) if sr else None
        
        if rb_latest and sr_latest:
            return rb if rb_latest > sr_latest else sr
        elif rb_latest:
            return rb
        elif sr_latest:
            return sr
        return rb or sr or {}
    return {}

def write_current_track_to_file(output_dir="obs_output", source="auto"):
    """
    Writes current song information to files for OBS use.
    
    Uses deck data as the single source of truth. The 'current track'
    files show the most recently loaded track across all decks.
    
    Args:
        output_dir: Directory where files will be saved
        source: DJ software source to read from
    """
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        decks = get_current_tracks_by_deck(source)
        
        if not decks:
            # No decks found, try single track as fallback
            track_info = get_current_playing_track(source)
            if not track_info:
                # Nothing is loaded: blank current-track + deck outputs so
                # OBS shows nothing (history is kept).
                clear_current_track_files(output_dir)
                print("No song detected - files cleared")
                return False
            decks = {1: track_info}
        
        # Use the last deck as the "current" track for main files
        last_deck_id = max(decks.keys())
        track_info = decks[last_deck_id]
        
        artist_title = f"{track_info['artist']} - {track_info['title']}"
        track_source = track_info.get('source', source)

        # NOTE: history is NOT updated here. The current/deck files reflect what
        # is loaded right now; history is maintained separately by the monitor,
        # which only adds a track after it has been on a deck for the played
        # threshold (>30s). See monitor_and_update().

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
        
        for filename, filecontent in files_to_write.items():
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(filecontent)
        
        # Blank any existing deck folders first so decks that were unloaded
        # don't keep showing stale tracks, then write only the loaded decks.
        for deck_dir in glob.glob(os.path.join(output_dir, 'deck_*')):
            if os.path.isdir(deck_dir):
                for fn in ('current_track.txt', 'artist.txt', 'title.txt', 'album.txt'):
                    with open(os.path.join(deck_dir, fn), 'w', encoding='utf-8') as f:
                        f.write("")

        # Write per-deck output
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
        
        print(f"Files updated in '{output_dir}' (source: {track_source}):")
        print(f"   current_track.txt: {artist_title}")
        for deck_id, deck_track in sorted(decks.items()):
            print(f"   deck_{deck_id}/: {deck_track['artist']} - {deck_track['title']}")

        return True
            
    except Exception as e:
        print(f"Error writing files: {e}")
        return False


def clear_current_track_files(output_dir="obs_output"):
    """
    Blanks the 'currently playing' outputs when nothing is loaded, WITHOUT
    touching the play history.

    Empties the top-level current-track files and the files inside every
    deck_* folder. Files are EMPTIED (truncated), not deleted, because OBS
    keeps live references to these exact paths and reports "Missing Files"
    if they disappear.

    Args:
        output_dir: Directory where output files are stored
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Blank the top-level current-track files
    for filename in ('current_track.txt', 'artist.txt', 'title.txt',
                     'album.txt', 'full_info.txt'):
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("")
    # Reset JSON track info to a valid empty object
    with open(os.path.join(output_dir, 'track_info.json'), 'w', encoding='utf-8') as f:
        f.write("{}")

    # Blank every per-deck folder (deck_1, deck_2, ...) without removing it,
    # so OBS deck sources keep pointing at valid (empty) files.
    for deck_dir in glob.glob(os.path.join(output_dir, 'deck_*')):
        if os.path.isdir(deck_dir):
            for filename in ('current_track.txt', 'artist.txt', 'title.txt', 'album.txt'):
                filepath = os.path.join(deck_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("")


def clear_history(output_dir="obs_output"):
    """
    Resets ALL output for a fresh session: current-track files, deck folders,
    AND the play history.

    Files are EMPTIED (truncated), not deleted. OBS keeps live references to
    these exact file paths, so deleting them makes OBS report "Missing Files".
    Emptying keeps every path valid while clearing stale content.

    Args:
        output_dir: Directory where output files are stored
    """
    # Blank current-track + deck outputs
    clear_current_track_files(output_dir)

    # Blank the history text files (keep the files so OBS sources stay valid)
    for filename in ('history.txt', 'history_simple.txt', 'history_numbered.txt'):
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("")
    # Reset JSON history to a valid empty list
    with open(os.path.join(output_dir, 'history.json'), 'w', encoding='utf-8') as f:
        f.write("[]")


def update_music_history(track_info, output_dir="obs_output", max_history=15):
    """
    Updates the history file with the latest songs.
    
    Args:
        track_info: Current song information
        output_dir: Directory where to save
        max_history: Maximum number of songs in history
    """
    try:
        history_file = os.path.join(output_dir, 'history.txt')
        history_json_file = os.path.join(output_dir, 'history.json')
        
        history = []
        if os.path.exists(history_json_file):
            try:
                with open(history_json_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception:
                history = []
        
        current_entry = {
            'artist': track_info['artist'],
            'title': track_info['title'],
            'album': track_info['album'],
            'played_at': track_info['last_played'].strftime('%H:%M:%S'),
            'played_date': track_info['last_played'].strftime('%Y-%m-%d'),
            'track_number': track_info['track_number'],
            'source': track_info.get('source', 'unknown')
        }
        
        # Check for duplicates
        if not history or (history[0]['artist'] != current_entry['artist'] or 
                          history[0]['title'] != current_entry['title']):
            
            history.insert(0, current_entry)
            history = history[:max_history]
            
            # Save JSON history
            with open(history_json_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            # Formatted text for OBS
            with open(history_file, 'w', encoding='utf-8') as f:
                f.write("MUSIC HISTORY (Last 15)\n")
                f.write("=" * 50 + "\n\n")
                
                for i, track in enumerate(history, 1):
                    if i == 1:
                        f.write(f"{i:2d}. {track['artist']} - {track['title']} CURRENT\n")
                    else:
                        f.write(f"   {i:2d}. {track['artist']} - {track['title']}\n")
                    f.write(f"       Album: {track['album']} | Last Played: {track['played_at']}\n\n")
            
            # Simple version
            simple_history_file = os.path.join(output_dir, 'history_simple.txt')
            with open(simple_history_file, 'w', encoding='utf-8') as f:
                for i, track in enumerate(history, 1):
                    prefix = ">>> " if i == 1 else "    "
                    f.write(f"{prefix}{track['artist']} - {track['title']}\n")
            
            # Numbered version
            numbered_history_file = os.path.join(output_dir, 'history_numbered.txt')
            with open(numbered_history_file, 'w', encoding='utf-8') as f:
                for i, track in enumerate(history, 1):
                    marker = " (Current)" if i == 1 else ""
                    f.write(f"{i:2d}. {track['artist']} - {track['title']}{marker}\n")
    
    except Exception as e:
        print(f"Error updating history: {e}")


def monitor_and_update(output_dir="obs_output", interval=10, source="auto"):
    """
    Continuously monitors and updates files when the song changes.
    
    Args:
        output_dir: Directory where files will be saved
        interval: Interval in seconds to check for changes
        source: DJ software source to read from
    """
    source_label = source.upper()
    print(f"Starting continuous monitoring (source: {source_label})...")
    print(f"Files will be saved in: {os.path.abspath(output_dir)}")
    print(f" Checking every {interval} seconds")
    print("Press Ctrl+C to stop\n")
    
    # Start with a clean history for this session
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    clear_history(output_dir)
    print(f"Output cleared - fresh session (history threshold: {HISTORY_PLAYED_SECONDS}s)\n")

    last_decks = {}   # deck_id -> "artist - title" (last written snapshot)
    # Per-deck timing for the "played >Ns" history rule:
    #   deck_id -> {'track_id', 'since': datetime, 'in_history': bool, 'track': dict}
    deck_timers = {}

    try:
        while True:
            decks = get_current_tracks_by_deck(source)
            now = datetime.now()
            snapshot = {
                deck_id: f"{t['artist']} - {t['title']}"
                for deck_id, t in decks.items()
            }

            # --- History: add a track only after it has been on a deck >= N s ---
            for deck_id, track in decks.items():
                track_id = snapshot[deck_id]
                timer = deck_timers.get(deck_id)
                if not timer or timer['track_id'] != track_id:
                    # New track on this deck — start its timer
                    deck_timers[deck_id] = {
                        'track_id': track_id, 'since': now,
                        'in_history': False, 'track': track,
                    }
                else:
                    timer['track'] = track
                    if (not timer['in_history'] and
                            (now - timer['since']).total_seconds() >= HISTORY_PLAYED_SECONDS):
                        update_music_history(track, output_dir)
                        timer['in_history'] = True
                        print(f"+ History (played >{HISTORY_PLAYED_SECONDS}s): {track_id}")
            # Drop timers for decks no longer loaded
            for deck_id in list(deck_timers):
                if deck_id not in decks:
                    del deck_timers[deck_id]

            # --- Current/deck output: reflect real-time deck state ---
            if snapshot != last_decks:
                removed = set(last_decks) - set(snapshot)
                for deck_id in sorted(removed):
                    print(f"Deck {deck_id} unloaded")
                for deck_id in sorted(snapshot):
                    if last_decks.get(deck_id) != snapshot[deck_id]:
                        src = decks[deck_id].get('source', source)
                        print(f"Deck {deck_id} loaded [{src}]: {snapshot[deck_id]}")

                # Writes loaded decks (or blanks everything when nothing loaded)
                write_current_track_to_file(output_dir, source)
                last_decks = snapshot
            else:
                if snapshot:
                    deck_summary = " | ".join(
                        f"D{d}: {t}" for d, t in sorted(snapshot.items())
                    )
                    print(f"No changes [{deck_summary}]")

            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring interrupted by user")
    except Exception as e:
        print(f"\n Error in monitoring: {e}")


def print_current_track(source="auto"):
    """
    Prints current song information in a formatted way.
    """
    track_info = get_current_playing_track(source)
    
    if track_info:
        track_source = track_info.get('source', source).upper()
        print(f" CURRENT SONG ({track_source}) ")
        print("=" * 50)
        print(f"Title: {track_info['title']}")
        print(f"Artist: {track_info['artist']}")
        print(f"Album: {track_info['album']}")
        print(f"Genre: {track_info['genre']}")
        print(f"Last played: {track_info['last_played']}")
        print(f"History: {track_info['history_name']}")
        print(f"Track #: {track_info['track_number']}")
        print(f"File: {track_info['file_path']}")
        if track_info.get('key'):
            print(f"Key: {track_info['key']}")
        if track_info.get('hardware'):
            print(f"Hardware: {track_info['hardware']}")
        print("=" * 50)
    else:
        print(" Unable to find information about the current song")
        print("Make sure that:")
        print("- Rekordbox or Serato DJ Pro is running")
        print("- At least one song has been played")


def parse_args(args):
    """
    Parses command-line arguments.
    
    Returns:
        tuple: (command, source, interval, output_dir)
    """
    command = "show"
    source = "auto"
    interval = 10
    output_dir = "obs_output"
    
    # Extract --source flag from anywhere in args
    filtered_args = []
    i = 0
    while i < len(args):
        if args[i] == "--source" and i + 1 < len(args):
            source = args[i + 1].lower()
            i += 2
        else:
            filtered_args.append(args[i])
            i += 1
    
    if filtered_args:
        command = filtered_args[0].lower()
        
        if command == "monitor":
            if len(filtered_args) > 1:
                try:
                    interval = int(filtered_args[1])
                except ValueError:
                    pass
            if len(filtered_args) > 2:
                output_dir = filtered_args[2]
        
        elif command == "write":
            if len(filtered_args) > 1:
                output_dir = filtered_args[1]
    
    return command, source, interval, output_dir


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command, source, interval, output_dir = parse_args(sys.argv[1:])
        
        if command == "monitor":
            monitor_and_update(output_dir, interval, source)
        elif command == "write":
            write_current_track_to_file(output_dir, source)
        elif command == "show":
            print_current_track(source)
        else:
            print("DJ Track Monitor - OBS Integration")
            print("=" * 50)
            print("\nAvailable commands:")
            print("  python track.py show [--source rekordbox|serato|auto]")
            print("  python track.py write [dir] [--source rekordbox|serato|auto]")
            print("  python track.py monitor [sec] [dir] [--source rekordbox|serato|auto]")
            print("\nSources:")
            print("  rekordbox  - Read from Rekordbox DJ")
            print("  serato     - Read from Serato DJ Pro")
            print("  auto       - Auto-detect (default, picks most recent)")
            print("\nExamples:")
            print("  python track.py show --source serato")
            print("  python track.py monitor 5 --source rekordbox")
            print("  python track.py monitor 5 obs_files --source auto")
            print("  python track.py write my_obs_folder --source serato")
    else:
        print_current_track("auto")