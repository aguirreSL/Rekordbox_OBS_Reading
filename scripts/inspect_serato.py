import os
import glob
from serato_reader import parse_session_file, FIELD_DECK, FIELD_TITLE, FIELD_ARTIST, FIELD_PLAYED, FIELD_START_TIME, FIELD_END_TIME

session_dir = os.path.expanduser('~/Music/_Serato_/History/Sessions')
sessions = glob.glob(os.path.join(session_dir, '*.session'))
latest = max(sessions, key=os.path.getmtime)
print(f"Latest session: {latest}")

entries = parse_session_file(latest)
for entry in entries[-5:]:
    deck = entry.get(FIELD_DECK)
    title = entry.get(FIELD_TITLE)
    artist = entry.get(FIELD_ARTIST)
    played = entry.get(FIELD_PLAYED)
    st = entry.get(FIELD_START_TIME)
    et = entry.get(FIELD_END_TIME)
    print(f"Deck: {deck}, Title: {title}, Artist: {artist}, Played: {played}, Start: {st}, End: {et}")
