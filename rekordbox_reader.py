"""
Rekordbox database reader.

Extracts the currently playing track from Rekordbox's local SQLite database
using pyrekordbox. Also supports resolving Spotify track metadata via the
Spotify API when Spotify URI-based tracks are detected.
"""

from pyrekordbox import Rekordbox6Database
from sqlalchemy import desc
from datetime import datetime
import os
import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


# Spotify API client (cached globally)
spotify_client = None


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


def get_current_playing_track():
    """
    Queries which song was most recently played in Rekordbox.
    Searches for the song with the most recent 'created_at' timestamp
    across all history entries.
    
    Returns:
        dict: Current song information or None if not found
    """
    try:
        db = Rekordbox6Database()
        
        history_query = db.get_history()
        history_model = history_query.column_descriptions[0]['type']
        recent_histories = history_query.order_by(desc(history_model.DateCreated)).limit(5).all()
        
        if not recent_histories:
            return None
        
        most_recent_song = None
        most_recent_time = None
        source_history = None
        
        for history in recent_histories:
            if history.Songs:
                for song in history.Songs:
                    song_time = song.updated_at if song.updated_at else song.created_at
                    
                    if song_time and (most_recent_time is None or song_time > most_recent_time):
                        most_recent_song = song
                        most_recent_time = song_time
                        source_history = history
        
        if not most_recent_song:
            return None
            
        content = db.get_content().filter_by(ID=most_recent_song.ContentID).first()
        
        if not content:
            return None
        
        # Check if this is a Spotify track
        is_spotify_track = content.FolderPath and content.FolderPath.startswith('spotify:track:')
        spotify_info = None
        
        if is_spotify_track:
            spotify_info = get_spotify_track_info(content.FolderPath)
        
        # Extract artist (prioritize Spotify data)
        artist_name = "Unknown"
        if spotify_info:
            artist_name = spotify_info['artist']
        elif hasattr(content, 'ArtistName') and content.ArtistName:
            artist_name = content.ArtistName
        elif content.Artist and hasattr(content.Artist, 'Name'):
            artist_name = content.Artist.Name
        elif content.Artist:
            artist_name = str(content.Artist)
        
        # Extract album (prioritize Spotify data)
        album_name = "Unknown Album"
        if spotify_info:
            album_name = spotify_info['album']
        elif hasattr(content, 'AlbumName') and content.AlbumName:
            album_name = content.AlbumName
        elif content.Album and hasattr(content.Album, 'Name'):
            album_name = content.Album.Name
        elif content.Album:
            album_name = str(content.Album)
        
        # Extract title (prioritize Spotify data)
        title_name = "Unknown Title"
        if spotify_info:
            title_name = spotify_info['title']
        elif content.Title:
            title_name = content.Title
        
        # Extract genre
        genre_name = "Unknown Genre"
        if spotify_info:
            genre_name = spotify_info['genre']
        elif hasattr(content, 'GenreName') and content.GenreName:
            genre_name = content.GenreName
        elif content.Genre and hasattr(content.Genre, 'Name'):
            genre_name = content.Genre.Name
        elif content.Genre:
            genre_name = str(content.Genre)
            
        return {
            'title': title_name,
            'artist': artist_name,
            'album': album_name,
            'genre': genre_name, 
            'file_path': content.FolderPath or "Unknown Path",
            'last_played': most_recent_time,
            'history_name': source_history.Name,
            'track_number': most_recent_song.TrackNo,
            'is_spotify': is_spotify_track,
            'source': 'rekordbox'
        }
        
    except Exception as e:
        print(f"Error reading Rekordbox data: {e}")
        return None
