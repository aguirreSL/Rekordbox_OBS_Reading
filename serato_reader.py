"""
Serato DJ Pro session file reader.

Parses the binary session files stored in ~/Music/_Serato_/History/Sessions/
to extract the currently (or most recently) playing track information.

Session files use a Tag-Length-Value (TLV) binary format with big-endian
byte order and UTF-16BE encoded strings.
"""

import struct
import os
import glob
import subprocess
from datetime import datetime


# Serato session file field IDs
FIELD_ROW_ID = 0x01
FIELD_FILEPATH = 0x02
FIELD_TITLE = 0x06
FIELD_ARTIST = 0x07
FIELD_ALBUM = 0x08
FIELD_GENRE = 0x09
FIELD_BPM = 0x0F
FIELD_COMMENT = 0x11
FIELD_START_TIME = 0x1C
FIELD_END_TIME = 0x1D
FIELD_DECK = 0x1F
FIELD_PLAYTIME = 0x2D
FIELD_SESSION_ID = 0x30
FIELD_PLAYED = 0x32
FIELD_KEY = 0x33
FIELD_ADDED = 0x34
FIELD_TIMESTAMP = 0x35
FIELD_HARDWARE = 0x3F


def get_serato_session_dir():
    """
    Returns the path to the Serato session history directory.
    
    Returns:
        str: Path to the Sessions directory, or None if not found
    """
    serato_dir = os.path.expanduser("~/Music/_Serato_/History/Sessions")
    if os.path.isdir(serato_dir):
        return serato_dir
    return None


def find_latest_session():
    """
    Finds the most recently modified .session file.
    
    Returns:
        str: Path to the latest session file, or None if none found
    """
    session_dir = get_serato_session_dir()
    if not session_dir:
        return None
    
    sessions = glob.glob(os.path.join(session_dir, "*.session"))
    if not sessions:
        return None
    
    return max(sessions, key=os.path.getmtime)


def parse_session_file(filepath):
    """
    Parses a Serato session file and extracts all track entries.
    
    The file format is:
      - Header: 'vrsn' tag (4 bytes) + length (4 bytes) + UTF-16BE version string
      - Entries: 'oent' tag (4 bytes) + length (4 bytes) + entry data
        - Each entry contains: 'adat' tag (4 bytes) + length (4 bytes) + field data
          - Fields: field_id (4 bytes) + field_length (4 bytes) + field_data
    
    Args:
        filepath: Path to the .session file
        
    Returns:
        list[dict]: List of track entry dictionaries
    """
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
    except (IOError, OSError) as e:
        print(f"Error reading session file: {e}")
        return []
    
    if len(data) < 8:
        return []
    
    entries = []
    pos = 0
    
    # Skip the version header
    if data[0:4] == b'vrsn':
        header_len = struct.unpack('>I', data[4:8])[0]
        pos = 8 + header_len
    
    # Parse entries
    while pos + 8 <= len(data):
        tag = data[pos:pos+4]
        block_len = struct.unpack('>I', data[pos+4:pos+8])[0]
        
        if tag == b'oent':
            entry = _parse_entry(data[pos+8:pos+8+block_len])
            if entry:
                entries.append(entry)
        
        pos += 8 + block_len
    
    return entries


def _parse_entry(entry_data):
    """
    Parses a single 'oent' entry block.
    
    Args:
        entry_data: Raw bytes of the entry (after the oent tag+length)
        
    Returns:
        dict: Parsed field values, or None if parsing fails
    """
    if len(entry_data) < 8 or entry_data[:4] != b'adat':
        return None
    
    adat_len = struct.unpack('>I', entry_data[4:8])[0]
    adat_data = entry_data[8:8+adat_len]
    
    fields = {}
    apos = 0
    
    while apos + 8 <= len(adat_data):
        field_id = struct.unpack('>I', adat_data[apos:apos+4])[0]
        field_len = struct.unpack('>I', adat_data[apos+4:apos+8])[0]
        field_bytes = adat_data[apos+8:apos+8+field_len]
        
        if field_len > 4:
            # String fields are UTF-16BE encoded
            try:
                fields[field_id] = field_bytes.decode('utf-16-be').rstrip('\x00')
            except UnicodeDecodeError:
                fields[field_id] = field_bytes.hex()
        elif field_len == 4:
            fields[field_id] = struct.unpack('>I', field_bytes)[0]
        elif field_len == 1:
            fields[field_id] = field_bytes[0]
        else:
            fields[field_id] = field_bytes.hex()
        
        apos += 8 + field_len
    
    return fields


# Audio file extensions that Serato DJ Pro can play
AUDIO_EXTENSIONS = (
    '.mp3', '.m4a', '.wav', '.flac', '.aiff', '.aif',
    '.ogg', '.wma', '.alac', '.aac',
)


def _is_real_track_path(path):
    """
    Returns False for audio files that are not user tracks (Serato's own app
    resource sounds). Keeps real tracks loaded on the decks.
    """
    low = path.lower()
    if 'serato dj pro.app/' in low:   # app-bundle resource sounds
        return False
    return True


def _get_live_deck_files():
    """
    Uses lsof to detect audio files Serato currently has OPEN, which indicates
    a track that is actually PLAYING (not merely loaded/cued).

    Serato opens a deck's audio file while it plays it. A track that is only
    loaded/cued (paused) does NOT keep the file open, so lsof distinguishes
    "playing" from "loaded".

    Returns:
        list[str]: Absolute paths to audio files currently open (playing).
    """
    try:
        result = subprocess.run(
            ['lsof', '-c', 'Serato'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return []

        audio_files = []
        seen = set()
        for line in result.stdout.splitlines():
            # lsof columns: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME
            # NAME (path) is everything after the 8th column and may have spaces
            lower_line = line.lower()
            if not any(ext in lower_line for ext in AUDIO_EXTENSIONS):
                continue
            parts = line.split(None, 8)
            if len(parts) < 9:
                continue
            filepath = parts[8]
            if not filepath.lower().endswith(AUDIO_EXTENSIONS):
                continue
            if not _is_real_track_path(filepath):
                continue
            if filepath in seen:
                continue
            if os.path.isfile(filepath):
                seen.add(filepath)
                audio_files.append(filepath)

        return audio_files

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        print(f"Warning: Could not run lsof for live deck detection: {e}")
        return []


def _parse_artist_title_from_filename(filepath):
    """
    Extracts artist and title from a filename following the common
    DJ convention: 'Artist - Title.ext'
    
    Args:
        filepath: Full path to the audio file
        
    Returns:
        tuple: (artist, title)
    """
    basename = os.path.splitext(os.path.basename(filepath))[0]
    
    if ' - ' in basename:
        parts = basename.split(' - ', 1)
        return parts[0].strip(), parts[1].strip()
    
    return "Unknown Artist", basename.strip()


def _build_track_info_from_file(filepath, deck_number=0):
    """
    Builds a standardized track info dict from an audio file path.
    
    Parses artist/title from the filename convention 'Artist - Title.ext'.
    
    Args:
        filepath: Path to the audio file
        deck_number: Deck number (1-based) to assign
        
    Returns:
        dict: Standardized track information
    """
    artist, title = _parse_artist_title_from_filename(filepath)
    
    return {
        'title': title,
        'artist': artist,
        'album': "Unknown Album",
        'genre': "Unknown Genre",
        'file_path': filepath,
        'last_played': datetime.now(),
        'history_name': "Serato Live",
        'track_number': deck_number,
        'is_spotify': False,
        'key': "",
        'hardware': "",
        'deck': deck_number,
        'source': 'serato'
    }

# Path to Serato's SQLite database
SERATO_SQLITE_DB = os.path.expanduser(
    "~/Library/Application Support/Serato/Library/master.sqlite"
)


def _get_decks_from_sqlite():
    """
    Reads the currently loaded tracks per deck from Serato's SQLite database.
    
    Serato stores history entries with end_time = -1 for tracks that are
    currently loaded on a deck. The 'deck' column contains the deck number.
    This works regardless of play/pause state.
    
    Returns:
        dict: A mapping of deck number (int) to track information dict,
              or None if the database is not accessible.
    """
    import sqlite3 as sqlite3_mod
    
    if not os.path.isfile(SERATO_SQLITE_DB):
        return None
    
    try:
        conn = sqlite3_mod.connect(
            f"file:{SERATO_SQLITE_DB}?mode=ro",
            uri=True, timeout=2
        )
        conn.row_factory = sqlite3_mod.Row
        cursor = conn.cursor()
        
        # Tracks currently loaded on decks have end_time = -1
        cursor.execute("""
            SELECT deck, name, artist, album, genre, key, bpm,
                   file_name, start_time
            FROM history_entry
            WHERE end_time = -1
            ORDER BY start_time DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
        
        decks = {}
        for row in rows:
            try:
                deck_id = int(row['deck'])
            except (ValueError, TypeError):
                continue
            
            if deck_id <= 0 or deck_id in decks:
                continue
            
            start_time = row['start_time']
            try:
                last_played = datetime.fromtimestamp(start_time) if start_time else datetime.now()
            except (ValueError, OSError):
                last_played = datetime.now()
            
            decks[deck_id] = {
                'title': row['name'] or "Unknown Title",
                'artist': row['artist'] or "Unknown Artist",
                'album': row['album'] or "Unknown Album",
                'genre': row['genre'] or "Unknown Genre",
                'file_path': row['file_name'] or "",
                'last_played': last_played,
                'history_name': "Serato Live",
                'track_number': deck_id,
                'is_spotify': False,
                'key': row['key'] or "",
                'hardware': "",
                'deck': deck_id,
                'bpm': row['bpm'] or 0,
                'source': 'serato'
            }
        
        return decks if decks else None
        
    except Exception as e:
        print(f"Warning: Could not read Serato SQLite database: {e}")
        return None


def get_current_tracks_by_deck():
    """
    Gets the tracks currently PLAYING per deck on Serato DJ Pro (real-time).

    "Playing" (not merely loaded/cued) is detected with lsof: Serato keeps a
    deck's audio file open only while it plays it. A loaded-but-paused track is
    therefore excluded. Rich metadata and the real deck number come from the
    SQLite history_entry rows (end_time = -1), matched to the playing files by
    filename.

    The SQLite "end_time = -1" rows by themselves mark LOADED tracks (Serato
    writes the row on load), so they are not used alone — they are intersected
    with the lsof "playing" set. The session history file is never used.

    Returns:
        dict: Mapping of deck number (int) to track info. Empty dict means
              nothing is currently playing.
    """
    try:
        # lsof => files actually being read => the tracks that are PLAYING
        playing = _get_live_deck_files()
        if not playing:
            return {}

        playing_by_base = {}
        for path in playing:
            playing_by_base.setdefault(os.path.basename(path), path)

        # SQLite loaded-deck rows give metadata + real deck numbers
        loaded = _get_decks_from_sqlite() or {}

        decks = {}
        used = set()
        for deck_id, track in loaded.items():
            base = os.path.basename(track.get('file_path', '') or '')
            if base in playing_by_base:
                decks[deck_id] = track
                used.add(base)

        # Any playing file without a SQLite match: build info from the filename
        next_deck = max(decks) if decks else 0
        for base, path in playing_by_base.items():
            if base in used:
                continue
            next_deck += 1
            decks[next_deck] = _build_track_info_from_file(path, next_deck)

        return decks
    except Exception as e:
        print(f"Error reading Serato decks: {e}")
        return {}


def get_current_playing_track():
    """
    Gets the currently playing/loaded track from Serato DJ Pro.
    
    Derives from get_current_tracks_by_deck for consistency.
    
    Returns:
        dict: Track information or None if not found
    """
    decks = get_current_tracks_by_deck()
    if decks:
        last_deck_id = max(decks.keys())
        return decks[last_deck_id]
    return None
