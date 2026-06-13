import os

with open('track.py', 'r') as f:
    lines = f.readlines()

get_tracks_func = """
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

"""

idx = 0
for i, line in enumerate(lines):
    if line.startswith('def write_current_track_to_file'):
        idx = i
        break

lines.insert(idx, get_tracks_func)

with open('track_new.py', 'w') as f:
    f.writelines(lines)
