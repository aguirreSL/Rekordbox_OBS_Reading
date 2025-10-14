@echo off
REM Setup script for Rekordbox → OBS Integration (Windows)
REM This script sets up everything needed to run the system

echo Rekordbox → OBS Integration Setup
echo =====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Python found
python --version

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo Virtual environment ready

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install required packages
echo Installing required packages...
pip install -r requirements.txt

echo.
echo Setup completed successfully!
echo.
echo You can now run:
echo    - start_obs_monitor.bat  (to start monitoring)
echo    - stop_obs_monitor.bat   (to stop monitoring)
echo.
echo 📖 See README_OBS.md for detailed instructions
echo.
pause