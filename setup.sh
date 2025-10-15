#!/bin/bash

# Setup script for Rekordbox → OBS Integration (Mac/Linux)
# This script sets up everything needed to run the system

echo "Rekordbox → OBS Integration Setup"
echo "====================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed"
    echo "Please install Python 3.8+ from https://python.org"
    echo "Or use your system package manager:"
    echo "  - macOS: brew install python3"
    echo "  - Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  - CentOS/RHEL: sudo yum install python3 python3-pip"
    exit 1
fi

echo "Python found"
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment"
        exit 1
    fi
fi

echo "Virtual environment ready"

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install required packages
echo "Installing required packages..."
pip install -r requirements.txt

# Make shell scripts executable
chmod +x start_obs_monitor.sh
chmod +x stop_obs_monitor.sh

echo ""
echo "Setup completed successfully!"
echo ""
echo "You can now run:"
echo "   - ./start_obs_monitor.sh  (to start monitoring)"
echo "   - ./stop_obs_monitor.sh   (to stop monitoring)"
echo ""
echo "See README.md for detailed instructions"
echo ""