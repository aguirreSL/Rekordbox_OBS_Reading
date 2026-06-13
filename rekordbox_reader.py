"""
Rekordbox database reader.

Extracts the currently playing track from Rekordbox's local SQLite database
using pyrekordbox. Also supports resolving Spotify track metadata via the
Spotify API when Spotify URI-based tracks are detected.
"""

from pyrekordbox import Rekordbox6Database
from datetime import datetime
import os
import re
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


# Spotify API client (cached globally)
spotify_client = None


def is_rekordbox_running():
    """
    Returns True if the Rekordbox application is currently running.

    When Rekordbox is closed there is nothing loaded, so detection must not
    report the last track left in the history database.

    Returns:
        bool: True if running (or if we cannot determine it), False if it is
              definitively not running.
    """
    try:
        # Exact process-name match (macOS/Linux executable is named 'rekordbox')
        result = subprocess.run(
            ['pgrep', '-x', 'rekordbox'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return True
        # Fallback: match the macOS app bundle path (won't match unrelated cmds)
        result = subprocess.run(
            ['pgrep', '-f', 'rekordbox.app/Contents/MacOS'],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # Can't determine (e.g. pgrep missing) — don't block detection
        return True


def get_spotify_client():
    """
    Get or create Spotify client (requires SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET env vars)
    """
    global spotify_client
    if spotify_client is None:
        try:
            client_id = os.environ.get('SPOTIFY_CLIENT_ID')
            client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
            
            if client_id and client_secret:
                auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
                spotify_client = spotipy.Spotify(auth_manager=auth_manager)
                return spotify_client
            else:
                return None
        except Exception:
            return None
    return spotify_client


def get_spotify_track_info(spotify_uri):
    """
    Fetch track information from Spotify API
    
    Args:
        spotify_uri: Spotify URI like 'spotify:track:6WRqUrMtWRWOSfnVY69zl3'
    
    Returns:
        dict: Track information or None if not found
    """
    try:
        match = re.search(r'spotify:track:([a-zA-Z0-9]+)', spotify_uri)
        if not match:
            return None
        
        track_id = match.group(1)
        
        sp = get_spotify_client()
        if not sp:
            return None
        
        track = sp.track(track_id)
        
        if track:
            artists = ', '.join([artist['name'] for artist in track['artists']])
            album = track['album']['name']
            
            return {
                'title': track['name'],
                'artist': artists,
                'album': album,
                'genre': 'Spotify',
                'is_spotify': True
            }
    except Exception:
        pass
    
    return None


# Audio file extensions Rekordbox can load
AUDIO_EXTENSIONS = (
    '.mp3', '.m4a', '.wav', '.flac', '.aiff', '.aif',
    '.ogg', '.wma', '.alac', '.aac',
)


def _is_real_track_path(path):
    """
    Returns False for audio files that are NOT user tracks loaded on a deck.

    Rekordbox keeps many internal audio files open (sampler banks, UI click
    sounds bundled in the app). Those must be ignored so only real tracks
    loaded on the decks are detected.
    """
    low = path.lower()
    if 'rekordbox.app/' in low:      # app-bundle resources (click sounds, etc.)
        return False
    if '/sampler/' in low:           # Rekordbox sampler preset banks
        return False
    return True


def _get_live_rekordbox_files():
    """
    Uses lsof to detect track audio files currently open by Rekordbox.

    Rekordbox keeps the audio file of each loaded deck open as a file
    descriptor, so this detects what is loaded in REAL TIME (no dependency on
    the history database, which only updates once Rekordbox decides a track
    counts as "played").

    Returns:
        list[str]: Absolute paths to user track files currently open.
    """
    try:
        result = subprocess.run(
            ['lsof', '-c', 'rekordbox'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return []

        files = []
        seen = set()
        for line in result.stdout.splitlines():
            lower_line = line.lower()
            if not any(ext in lower_line for ext in AUDIO_EXTENSIONS):
                continue
            # lsof columns: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME
            # NAME (the path) is everything after the 8th column and may contain spaces
            parts = line.split(None, 8)
            if len(parts) < 9:
                continue
            path = parts[8]
            if not path.lower().endswith(AUDIO_EXTENSIONS):
                continue
            if not _is_real_track_path(path):
                continue
            if path in seen:
                continue
            if os.path.isfile(path):
                seen.add(path)
                files.append(path)
        return files

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        print(f"Warning: Could not run lsof for Rekordbox live detection: {e}")
        return []


def _content_to_metadata(content):
    """
    Extracts (title, artist, album, genre, is_spotify) from a Rekordbox
    content row, resolving Spotify metadata when the track is a Spotify URI.
    """
    is_spotify_track = bool(content.FolderPath and content.FolderPath.startswith('spotify:track:'))
    spotify_info = get_spotify_track_info(content.FolderPath) if is_spotify_track else None

    # Artist (prioritize Spotify data)
    artist_name = "Unknown"
    if spotify_info:
        artist_name = spotify_info['artist']
    elif hasattr(content, 'ArtistName') and content.ArtistName:
        artist_name = content.ArtistName
    elif content.Artist and hasattr(content.Artist, 'Name'):
        artist_name = content.Artist.Name
    elif content.Artist:
        artist_name = str(content.Artist)

    # Album (prioritize Spotify data)
    album_name = "Unknown Album"
    if spotify_info:
        album_name = spotify_info['album']
    elif hasattr(content, 'AlbumName') and content.AlbumName:
        album_name = content.AlbumName
    elif content.Album and hasattr(content.Album, 'Name'):
        album_name = content.Album.Name
    elif content.Album:
        album_name = str(content.Album)

    # Title (prioritize Spotify data)
    title_name = "Unknown Title"
    if spotify_info:
        title_name = spotify_info['title']
    elif content.Title:
        title_name = content.Title

    # Genre (prioritize Spotify data)
    genre_name = "Unknown Genre"
    if spotify_info:
        genre_name = spotify_info['genre']
    elif hasattr(content, 'GenreName') and content.GenreName:
        genre_name = content.GenreName
    elif content.Genre and hasattr(content.Genre, 'Name'):
        genre_name = content.Genre.Name
    elif content.Genre:
        genre_name = str(content.Genre)

    return title_name, artist_name, album_name, genre_name, is_spotify_track


def _build_rekordbox_track_from_file(filepath, deck, db=None):
    """
    Builds a standardized track-info dict for a file currently loaded on a
    Rekordbox deck (detected via lsof).

    Metadata comes from the Rekordbox library (content table, which has no
    history delay). Falls back to parsing 'Artist - Title' from the filename
    if the file isn't found in the library.
    """
    title = artist = album = genre = None
    is_spotify = False

    if db is not None:
        try:
            content = db.get_content().filter_by(FolderPath=filepath).first()
            if content:
                title, artist, album, genre, is_spotify = _content_to_metadata(content)
        except Exception:
            pass

    if not title:
        # Fallback: parse 'Artist - Title.ext' from the filename
        basename = os.path.splitext(os.path.basename(filepath))[0]
        if ' - ' in basename:
            artist, title = (p.strip() for p in basename.split(' - ', 1))
        else:
            artist, title = "Unknown", basename.strip()
        album = album or "Unknown Album"
        genre = genre or "Unknown Genre"

    return {
        'title': title,
        'artist': artist,
        'album': album or "Unknown Album",
        'genre': genre or "Unknown Genre",
        'file_path': filepath,
        'last_played': datetime.now(),
        'history_name': "Rekordbox Live",
        'track_number': deck,
        'is_spotify': is_spotify,
        'deck': deck,
        'source': 'rekordbox'
    }


def get_current_tracks_by_deck():
    """
    Gets the tracks currently LOADED on Rekordbox decks, in REAL TIME.

    Detection uses lsof only: Rekordbox keeps the audio file of each loaded
    deck open as a file descriptor, so this reflects each deck the moment a
    track is loaded. The play-history database is intentionally NOT used — it
    only lists tracks that already passed Rekordbox's "played" threshold
    (e.g. 30s), which lags behind and does not represent what is on the decks.

    Returns:
        dict: Mapping of deck number (int) to track-info dict. Empty if nothing
              is loaded or Rekordbox is not running.
    """
    if not is_rekordbox_running():
        return {}

    live_files = _get_live_rekordbox_files()
    if not live_files:
        return {}

    # Open the library only to enrich metadata for the loaded files.
    db = None
    try:
        db = Rekordbox6Database()
    except Exception as e:
        print(f"Warning: Could not open Rekordbox database: {e}")

    decks = {}
    for i, filepath in enumerate(live_files):
        deck_id = i + 1
        decks[deck_id] = _build_rekordbox_track_from_file(filepath, deck_id, db)
    return decks


def get_current_playing_track():
    """
    Gets the track currently loaded on a Rekordbox deck (real-time, via lsof).

    Derived from get_current_tracks_by_deck for consistency. Returns None when
    nothing is loaded or Rekordbox isn't running.

    Returns:
        dict: Track information or None if not found
    """
    decks = get_current_tracks_by_deck()
    if decks:
        last_deck_id = max(decks.keys())
        return decks[last_deck_id]
    return None
