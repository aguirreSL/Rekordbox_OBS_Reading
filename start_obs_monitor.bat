@echo off
REM Script to start DJ track monitoring for OBS (Windows)
REM Supports both Rekordbox and Serato DJ Pro
REM Usage: start_obs_monitor.bat [--source rekordbox|serato|auto]

set SOURCE=auto

REM Parse --source argument
:parse_args
if "%~1"=="" goto done_args
if "%~1"=="--source" (
    set SOURCE=%~2
    shift
)
shift
goto parse_args
:done_args

echo Starting DJ → OBS integration
echo  Source: %SOURCE%
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
python track.py monitor 10 --source %SOURCE%