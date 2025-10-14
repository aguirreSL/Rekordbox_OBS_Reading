#!/bin/bash

# Script to start Rekordbox monitoring for OBS
# Usage: ./start_obs_monitor.sh

echo "Starting Rekordbox → OBS integration"
echo "📁 Output folder: $(pwd)/obs_output"
echo "⏱️ Checking for changes every 10 seconds"
echo ""
echo "To stop, press Ctrl+C"
echo ""

# Activate virtual environment and start monitoring
source venv/bin/activate
python track.py monitor 10