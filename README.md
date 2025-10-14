# Rekordbox OBS Integration

A real-time music information system that extracts currently playing track data from Rekordbox and provides it to OBS Studio for live streaming integration.

## Overview

<img width="714" height="603" alt="Screenshot 2025-10-14 at 20 16 29" src="https://github.com/user-attachments/assets/39524d29-beef-40bc-b4c9-abac7d1ce72c" />
<img width="698" height="452" alt="Screenshot 2025-10-14 at 20 22 25" src="https://github.com/user-attachments/assets/8e4a1852-cab8-4604-84a9-10e5f792e751" />


This tool monitors Rekordbox's database for track changes and automatically generates multiple text files containing current song information. These files can be used as text sources in OBS Studio to display real-time music information during live streams or recordings.

## System Requirements

- **Rekordbox**: Version 6.2.0 or higher
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
   pip install pyrekordbox sqlalchemy
   ```

## Usage

### Starting the Monitor

**Windows:**
```cmd
start_obs_monitor.bat
```

**macOS/Linux:**
```bash
./start_obs_monitor.sh
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

### Detection Method

The system uses timestamp-based detection to identify track changes in Rekordbox's database. This provides reliable change detection with a typical delay of 1-2 minutes after track transitions.

### Database Access

- Reads from Rekordbox's local SQLite database
- No modification of Rekordbox data
- Uses SQLAlchemy for robust database queries

### History Management

- Maintains rolling history of last 15 tracks
- Automatic duplicate prevention
- Persistent storage across restarts

## Troubleshooting

### Common Issues

**No track detection:**
- Ensure Rekordbox is running and playing music
- Verify database file location (typically in Music/Pioneer/rekordbox/)
- Check that Python has read access to the database

**File encoding problems:**
- All output files use UTF-8 encoding
- Ensure OBS text sources are configured for UTF-8

**Performance considerations:**
- Monitor uses minimal system resources
- Database queries are optimized for efficiency
- Background process runs independently

### Command Line Usage

**View current track:**
```bash
python track.py
```

**Monitor mode:**
```bash
python track.py monitor
```

## File Structure

```
RekordboxReading/
├── track.py                 # Main application
├── setup.sh/.bat           # Installation scripts
├── start_obs_monitor.sh/.bat # Start monitoring
├── stop_obs_monitor.sh/.bat  # Stop monitoring
├── obs_output/              # Generated text files
└── venv/                   # Python virtual environment
```

## Dependencies

- **pyrekordbox** (0.4.4): Rekordbox database access
- **sqlalchemy** (2.0.44): Database query framework

## License

Open source software. See source code for implementation details.

## Support

For issues or questions:
1. Verify Rekordbox is running and playing music
2. Check that all dependencies are properly installed
3. Ensure proper file permissions for database access
4. Review console output for error messages
## Support

For issues or questions:
1. Verify Rekordbox is running and playing music
2. Check that all dependencies are properly installed
3. Ensure proper file permissions for database access
4. Review console output for error messages
