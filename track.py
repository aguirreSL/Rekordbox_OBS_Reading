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


# A track is added to the history only after it has been PLAYING continuously
# for this many seconds, not the moment it's loaded/cued. Matches Rekordbox's
# "played" threshold. Tune via env var.
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

def write_decks_to_files(decks, output_dir="obs_output", source="auto", verbose=True):
    """
    Writes the given PLAYING decks to the OBS output files.

    Args:
        decks: mapping deck_id -> track-info for the tracks playing right now.
               If empty, current/deck outputs are blanked (history untouched).
        output_dir: Directory where files will be saved
        source: DJ software source label
        verbose: print a summary line

    Note: history is NOT updated here. The current/deck files reflect what is
    PLAYING right now; history is maintained by the monitor, which only adds a
    track after it has been playing for the played threshold (>30s).
    """
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if not decks:
            # Nothing playing: blank current-track + deck outputs (history kept)
            clear_current_track_files(output_dir)
            if verbose:
                print("Nothing playing - current/deck files cleared")
            return False

        # Use the highest deck as the "current" track for the main files
        last_deck_id = max(decks.keys())
        track_info = decks[last_deck_id]
        artist_title = f"{track_info['artist']} - {track_info['title']}"
        track_source = track_info.get('source', source)

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

        # Blank any existing deck folders first so decks that stopped playing
        # don't keep showing stale tracks, then write only the playing decks.
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

            deck_files_to_write = {
                'current_track.txt': f"{deck_track['artist']} - {deck_track['title']}",
                'artist.txt': deck_track['artist'],
                'title.txt': deck_track['title'],
                'album.txt': deck_track['album'],
            }
            for filename, filecontent in deck_files_to_write.items():
                filepath = os.path.join(deck_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(filecontent)

        if verbose:
            print(f"Files updated in '{output_dir}' (source: {track_source}):")
            print(f"   current_track.txt: {artist_title}")
            for deck_id, deck_track in sorted(decks.items()):
                print(f"   deck_{deck_id}/: {deck_track['artist']} - {deck_track['title']}")

        return True

    except Exception as e:
        print(f"Error writing files: {e}")
        return False


def write_current_track_to_file(output_dir="obs_output", source="auto"):
    """
    One-shot: read what is PLAYING now and write it to the OBS files.
    Used by the `write` CLI command.
    """
    decks = get_current_tracks_by_deck(source)
    return write_decks_to_files(decks, output_dir, source)


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
            
            # Formatted text for OBS (no "current" marker — clean list)
            with open(history_file, 'w', encoding='utf-8') as f:
                f.write("MUSIC HISTORY (Last 15)\n")
                f.write("=" * 50 + "\n\n")
                for i, track in enumerate(history, 1):
                    f.write(f"{i:2d}. {track['artist']} - {track['title']}\n")
                    f.write(f"       Album: {track['album']} | Last Played: {track['played_at']}\n\n")

            # Simple version
            simple_history_file = os.path.join(output_dir, 'history_simple.txt')
            with open(simple_history_file, 'w', encoding='utf-8') as f:
                for track in history:
                    f.write(f"{track['artist']} - {track['title']}\n")

            # Numbered version
            numbered_history_file = os.path.join(output_dir, 'history_numbered.txt')
            with open(numbered_history_file, 'w', encoding='utf-8') as f:
                for i, track in enumerate(history, 1):
                    f.write(f"{i:2d}. {track['artist']} - {track['title']}\n")
    
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

    def key(track):
        return track.get('file_path') or f"{track['artist']} - {track['title']}"

    playing_since = {}   # track key -> first time it was seen playing
    added = set()        # track keys already written to history this session
    empty_polls = 0      # consecutive polls with nothing playing (anti-flicker)
    last_snapshot = None

    try:
        while True:
            now = datetime.now()
            decks = get_current_tracks_by_deck(source)   # what's PLAYING now

            # History: add a track once it has played >= threshold seconds
            keys_now = set()
            for track in decks.values():
                k = key(track)
                keys_now.add(k)
                playing_since.setdefault(k, now)
                if k not in added and (now - playing_since[k]).total_seconds() >= HISTORY_PLAYED_SECONDS:
                    update_music_history(track, output_dir)
                    added.add(k)
                    print(f"+ History: {track['artist']} - {track['title']}")
            # Forget tracks that stopped (a later replay restarts their timer)
            for k in set(playing_since) - keys_now:
                del playing_since[k]

            # Anti-flicker: ignore a single empty poll (brief lsof gap) before
            # blanking the display.
            if not decks:
                empty_polls += 1
                if empty_polls == 1 and last_snapshot:
                    time.sleep(interval)
                    continue
            else:
                empty_polls = 0

            snapshot = {d: f"{t['artist']} - {t['title']}" for d, t in decks.items()}
            if snapshot != last_snapshot:
                prev = last_snapshot or {}
                for d in sorted(set(prev) - set(snapshot)):
                    print(f"Deck {d} stopped")
                for d in sorted(snapshot):
                    if prev.get(d) != snapshot[d]:
                        print(f"Deck {d} playing: {snapshot[d]}")
                write_decks_to_files(decks, output_dir, source, verbose=False)
                last_snapshot = snapshot

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