#!/bin/bash

echo "Spotify API Setup Helper"
echo "========================"
echo ""
echo "To enable Spotify track metadata:"
echo ""
echo "1. Go to: https://developer.spotify.com/dashboard"
echo "2. Log in and create a new app"
echo "3. Copy your Client ID and Client Secret"
echo "4. Run these commands:"
echo ""
echo "   export SPOTIFY_CLIENT_ID=\"your_client_id\""
echo "   export SPOTIFY_CLIENT_SECRET=\"your_client_secret\""
echo ""
echo "5. Then run: ./start_obs_monitor.sh"
echo ""
echo "Current status:"
if [ -n "$SPOTIFY_CLIENT_ID" ]; then
    echo "  ✓ SPOTIFY_CLIENT_ID is set"
else
    echo "  ✗ SPOTIFY_CLIENT_ID is not set"
fi

if [ -n "$SPOTIFY_CLIENT_SECRET" ]; then
    echo "  ✓ SPOTIFY_CLIENT_SECRET is set"
else
    echo "  ✗ SPOTIFY_CLIENT_SECRET is not set"
fi

echo ""
echo "Note: Spotify API is optional. Local music files work without it."
