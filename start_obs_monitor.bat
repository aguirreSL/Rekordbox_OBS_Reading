@echo off
REM Script to start Rekordbox monitoring for OBS (Windows)
REM Usage: start_obs_monitor.bat

echo Starting Rekordbox → OBS integration
echo  Output folder: %cd%\obs_output
echo  Checking for changes every 10 seconds
echo.
echo To stop, press Ctrl+C
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment and start monitoring
call venv\Scripts\activate.bat
python track.py monitor 10