import pyrekordbox
from pyrekordbox import Rekordbox6Database
from sqlalchemy import desc

db = Rekordbox6Database()
history_query = db.get_history()
history_model = history_query.column_descriptions[0]['type']
recent = history_query.order_by(desc(history_model.DateCreated)).limit(1).first()

if recent and recent.Songs:
    song = recent.Songs[-1]
    print(dir(song))
    print({k: getattr(song, k) for k in dir(song) if not k.startswith('_')})
