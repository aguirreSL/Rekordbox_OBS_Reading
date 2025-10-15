@echo off
REM Script to stop Rekordbox monitoring for OBS (Windows)
REM Usage: stop_obs_monitor.bat

echo Stopping Rekordbox → OBS integration...

REM Find and kill the process
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| findstr "track.py"') do (
    echo Found Python process: %%i
    taskkill /PID %%i /F >nul 2>&1
)

REM Alternative method using WMIC
wmic process where "CommandLine like '%%track.py monitor%%'" delete >nul 2>&1

echo Monitoring stopped!
echo System stopped. Run start_obs_monitor.bat to restart.
pause