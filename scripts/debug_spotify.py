from pyrekordbox import Rekordbox6Database
from sqlalchemy import desc

# Connect to Rekordbox database
db = Rekordbox6Database()

# Get the most recent history entries (check multiple)
history_query = db.get_history()
history_model = history_query.column_descriptions[0]['type']
recent_histories = history_query.order_by(desc(history_model.DateCreated)).limit(5).all()

print("=== Checking Last 5 Songs ===\n")

for idx, history in enumerate(recent_histories, 1):
    if history.Songs:
        for song in history.Songs:
            # Use created_at or updated_at to find the most recent
            song_time = song.updated_at if song.updated_at else song.created_at
            
            content = db.get_content().filter_by(ID=song.ContentID).first()
            
            if content:
                print(f"Song {idx} - Track #{song.TrackNo}")
                print(f"  Time: {song_time}")
                print(f"  Title: {content.Title}")
                print(f"  ArtistName: {getattr(content, 'ArtistName', 'N/A')}")
                print(f"  AlbumName: {getattr(content, 'AlbumName', 'N/A')}")
                print(f"  FolderPath: {content.FolderPath}")
                print()
