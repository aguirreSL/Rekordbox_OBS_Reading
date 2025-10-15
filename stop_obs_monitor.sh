#!/bin/bash

# Script to stop Rekordbox monitoring for OBS
# Usage: ./stop_obs_monitor.sh

echo "Stopping Rekordbox → OBS integration..."

# Find and kill the process
PIDS=$(ps aux | grep "track.py monitor" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "No monitoring process found"
else
    echo "🔍 Found process(es): $PIDS"
    kill $PIDS 2>/dev/null
    sleep 1
    
    # Check if still running
    REMAINING=$(ps aux | grep "track.py monitor" | grep -v grep | awk '{print $2}')
    if [ -z "$REMAINING" ]; then
        echo "Monitoring stopped successfully!"
    else
        echo " Force stopping..."
        kill -9 $REMAINING 2>/dev/null
        echo "Process terminated forcefully"
    fi
fi

echo "System stopped. Run ./start_obs_monitor.sh to restart."