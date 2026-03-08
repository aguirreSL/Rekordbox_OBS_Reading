#!/bin/bash

# Script to start DJ track monitoring for OBS
# Supports both Rekordbox and Serato DJ Pro
# Usage: ./start_obs_monitor.sh [--source rekordbox|serato|auto]

SOURCE="auto"

# Parse arguments
for arg in "$@"; do
    if [ "$prev_arg" = "--source" ]; then
        SOURCE="$arg"
    fi
    prev_arg="$arg"
done

echo "Starting DJ → OBS integration"
echo " Source: $SOURCE"
echo " Output folder: $(pwd)/obs_output"
echo " Checking for changes every 10 seconds"
echo ""
echo "To stop, press Ctrl+C"
echo ""

# Activate virtual environment and start monitoring
source venv/bin/activate
python track.py monitor 10 --source "$SOURCE"