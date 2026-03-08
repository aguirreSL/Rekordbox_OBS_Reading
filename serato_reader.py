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


def _entry_to_track_info(entry, session_path=None):
    """
    Converts a raw parsed entry dict into the standard track info format
    used by the rest of the application.
    
    Args:
        entry: Dict of field_id -> value from parse_session_file
        session_path: Path of the source session file
        
    Returns:
        dict: Standardized track information
    """
    # Extract timestamp
    timestamp = entry.get(FIELD_TIMESTAMP) or entry.get(FIELD_END_TIME) or entry.get(FIELD_START_TIME)
    last_played = None
    if timestamp and isinstance(timestamp, int) and timestamp > 0:
        try:
            last_played = datetime.fromtimestamp(timestamp)
        except (ValueError, OSError):
            last_played = datetime.now()
    else:
        last_played = datetime.now()
    
    # Determine track number from row ID
    track_number = entry.get(FIELD_ROW_ID, 0)
    
    # Extract the session ID for history name
    session_id = entry.get(FIELD_SESSION_ID, 0)
    session_name = f"Serato Session {session_id}"
    if session_path:
        session_name = f"Serato - {os.path.basename(session_path)}"
    
    return {
        'title': entry.get(FIELD_TITLE, "Unknown Title"),
        'artist': entry.get(FIELD_ARTIST, "Unknown Artist"),
        'album': entry.get(FIELD_ALBUM, "Unknown Album"),
        'genre': entry.get(FIELD_GENRE, "Unknown Genre"),
        'file_path': entry.get(FIELD_FILEPATH, "Unknown Path"),
        'last_played': last_played,
        'history_name': session_name,
        'track_number': track_number,
        'is_spotify': False,
        'key': entry.get(FIELD_KEY, ""),
        'hardware': entry.get(FIELD_HARDWARE, ""),
        'source': 'serato'
    }


def get_current_playing_track():
    """
    Gets the most recently played track from Serato DJ Pro.
    
    Reads the latest session file and returns the last entry,
    which represents the most recently played/loaded track.
    
    Returns:
        dict: Track information or None if not found
    """
    try:
        session_path = find_latest_session()
        if not session_path:
            return None
        
        entries = parse_session_file(session_path)
        if not entries:
            return None
        
        # The last entry in the session is the most recent track
        latest_entry = entries[-1]
        
        return _entry_to_track_info(latest_entry, session_path)
        
    except Exception as e:
        print(f"Error reading Serato data: {e}")
        return None


def get_latest_session_mtime():
    """
    Returns the modification time of the latest session file,
    useful for 'auto' source detection.
    
    Returns:
        float: Modification time as Unix timestamp, or 0 if not found
    """
    session_path = find_latest_session()
    if session_path:
        return os.path.getmtime(session_path)
    return 0
