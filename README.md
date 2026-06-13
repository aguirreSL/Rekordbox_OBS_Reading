# DJ OBS Integration (Rekordbox + Serato DJ Pro)

A real-time music information system that extracts currently playing track data from **Rekordbox** or **Serato DJ Pro** and provides it to OBS Studio for live streaming integration.

## Overview

<img width="714" height="603" alt="Screenshot 2025-10-14 at 20 16 29" src="https://github.com/user-attachments/assets/39524d29-beef-40bc-b4c9-abac7d1ce72c" />
<img width="698" height="452" alt="Screenshot 2025-10-14 at 20 22 25" src="https://github.com/user-attachments/assets/8e4a1852-cab8-4604-84a9-10e5f792e751" />


This tool monitors your DJ software's database/session files for track changes and automatically generates multiple text files containing current song information. These files can be used as text sources in OBS Studio to display real-time music information during live streams or recordings.

### Supported DJ Software

| Software | Detection Method | Notes |
|----------|-----------------|-------|
| **Rekordbox** (6.2.0+) | SQLite database | 1-2 min delay after track transitions |
| **Serato DJ Pro** | Session history files | Near real-time detection |

## System Requirements

- **DJ Software**: Rekordbox 6.2.0+ or Serato DJ Pro
- **Python**: Version 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **OBS Studio**: Any recent version (for text source integration)

## Installation

### Automated Setup

**Windows:**
```cmd
setup.bat
```

**macOS/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

### Manual Installation

1. **Clone or download this repository**
2. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```
3. **Activate virtual environment:**
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Choosing Your DJ Software Source

Use the `--source` flag to specify which DJ software to read from:

| Flag | Description |
|------|-------------|
| `--source auto` | **Default.** Tries both sources, picks the most recently played track |
| `--source rekordbox` | Read only from Rekordbox |
| `--source serato` | Read only from Serato DJ Pro |

### Starting the Monitor

**Windows:**
```cmd
start_obs_monitor.bat
start_obs_monitor.bat --source serato
```

**macOS/Linux:**
```bash
./start_obs_monitor.sh
./start_obs_monitor.sh --source serato
```

### Stopping the Monitor

**Windows:**
```cmd
stop_obs_monitor.bat
```

**macOS/Linux:**
```bash
./stop_obs_monitor.sh
```

### Command Line Usage

```bash
# Show current track (auto-detect source)
python track.py show

# Show current track from specific source
python track.py show --source serato
python track.py show --source rekordbox

# Write files once
python track.py write --source serato

# Monitor continuously (check every 5 seconds, Serato source)
python track.py monitor 5 --source serato

# Monitor with custom output directory
python track.py monitor 10 obs_files --source auto
```

### Output Files

The system creates an `obs_output` directory containing multiple file formats:

| File | Content | Use Case |
|------|---------|----------|
| `current_track.txt` | Artist - Title | Basic OBS text source |
| `artist.txt` | Artist name only | Separate artist display |
| `title.txt` | Song title only | Separate title display |
| `album.txt` | Album name | Album information |
| `history.txt` | Last 15 tracks with formatting | Detailed history display |
| `history_simple.txt` | Last 15 tracks (basic format) | Clean history list |
| `history_numbered.txt` | Numbered track list | Numbered display |
| `track_info.json` | Complete track metadata | Advanced integrations |
| `history.json` | Historical data in JSON | Programmatic access |

## OBS Studio Integration

### Adding Text Sources

1. **Add Text Source:**
   - Click "+" in Sources panel
   - Select "Text (GDI+)" or "Text (FreeType 2)"

2. **Configure File Input:**
   - Check "Read from file"
   - Browse to `obs_output/current_track.txt`
   - Configure font, color, and positioning

3. **Advanced Setup:**
   - Create separate sources for artist and title
   - Use `artist.txt` and `title.txt` for independent styling
   - Add `history.txt` for track history displays

### Recommended OBS Settings

- **Update frequency:** Text sources refresh automatically
- **File encoding:** UTF-8 (handles international characters)
- **Font recommendations:** Monospace fonts for consistent formatting

## Technical Details

### Rekordbox Detection

Detection uses **lsof** — Rekordbox opens a deck's audio file while it plays it,
so this reflects what is playing in real time (no delay).

- Returns nothing when Rekordbox is **not running**
- Internal audio (sampler banks, app UI sounds) is filtered out; only real
  user tracks are detected
- Track metadata (artist/title/album/genre) is read from the Rekordbox library
  (content table) via pyrekordbox; falls back to parsing `Artist - Title` from
  the filename if the file isn't in the library
- The play-**history** database is intentionally **not** used: it only logs
  tracks after they pass Rekordbox's "played" threshold (e.g. 30s), so it lags
  and does not represent what is on the decks right now
- No modification of Rekordbox data

### Serato DJ Pro Detection

Detection reports only what is **actually playing** (not merely loaded/cued):

1. **lsof** — Serato opens a deck's audio file only while it is **playing** it.
   A loaded-but-paused (cued) track keeps no file open, so lsof distinguishes
   "playing" from "loaded". This is the source of truth for what's on air.
2. **SQLite database** (`~/Library/Application Support/Serato/Library/master.sqlite`)
   — rows with `end_time = -1` (loaded tracks) provide rich metadata (artist,
   title, album, key, BPM) and the real deck number, matched to the playing
   files by filename.

Note: Serato writes the `end_time = -1` row on **load**, so SQLite alone marks
*loaded* tracks; it is intersected with lsof to keep only the *playing* ones.
The session history files in `~/Music/_Serato_/History/Sessions/` are not used.

### Current Track vs. History

These are two distinct outputs:

- **Current / per-deck files** reflect what is **playing right now** (real-time,
  via lsof). A track that is only loaded/cued (paused) is **not** shown — only
  audible tracks. If nothing is playing, the files are left empty.
- **History files** list tracks that actually **played**: a track is added to
  the history only after it has been playing continuously for the played
  threshold (default **30s**, set via `HISTORY_PLAYED_SECONDS`). Cueing or
  quickly swapping a track does not add it to history.

A single empty detection poll (brief lsof gap) is ignored before blanking, so a
playing track does not flicker out of the display.

History details:
- Rolling history of the last 15 played tracks
- Consecutive-duplicate prevention
- Tracks which source (Rekordbox/Serato) each song came from
- Cleared at the start of every monitoring session

## Troubleshooting

### Rekordbox Issues

**No track detection:**
- Ensure Rekordbox is running and playing music
- Verify database file location (typically in Music/Pioneer/rekordbox/)
- Check that Python has read access to the database

### Serato DJ Pro Issues

**No track detection:**
- Ensure Serato DJ Pro is running and has played at least one track
- Verify the `_Serato_` folder exists at `~/Music/_Serato_/`
- Check that session files exist in `~/Music/_Serato_/History/Sessions/`

**Stale track data:**
- Serato session files update when tracks are loaded/played
- Try loading a new track onto a deck

### General Issues

**File encoding problems:**
- All output files use UTF-8 encoding
- Ensure OBS text sources are configured for UTF-8

**Performance considerations:**
- Monitor uses minimal system resources
- Database/file queries are optimized for efficiency
- Background process runs independently

## File Structure

```
RekordboxReading/
├── track.py                 # Main application & CLI
├── rekordbox_reader.py      # Rekordbox database reader
├── serato_reader.py         # Serato session file parser
├── setup.sh/.bat            # Installation scripts
├── start_obs_monitor.sh/.bat # Start monitoring
├── stop_obs_monitor.sh/.bat  # Stop monitoring
├── obs_output/              # Generated text files
└── venv/                    # Python virtual environment
```

## Dependencies

- **pyrekordbox** (0.4.4): Rekordbox database access
- **sqlalchemy** (2.0.44): Database query framework
- **spotipy** (2.25.2): Spotify track metadata (optional, for Spotify-sourced tracks in Rekordbox)

> **Note:** Serato DJ Pro support requires no additional dependencies — it uses only Python's built-in modules.

## License

Open source software. See source code for implementation details.

## Support

For issues or questions:
1. Verify your DJ software is running and playing music
2. Check that all dependencies are properly installed
3. Ensure proper file permissions for database/file access
4. Try specifying the source explicitly: `--source rekordbox` or `--source serato`
5. Review console output for error messages
