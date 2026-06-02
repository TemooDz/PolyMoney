@echo off
:: Creates a Windows Task Scheduler entry to run polymarket_tracker.py
:: every Monday at 8:00 AM
:: Run this file once (right-click → Run as administrator)

SET SCRIPT_DIR=%~dp0
SET SCRIPT=%SCRIPT_DIR%polymarket_tracker.py
SET TASK_NAME=PolymarketWeeklyTracker

echo.
echo Creating scheduled task: %TASK_NAME%
echo Script: %SCRIPT%
echo Schedule: Every Monday at 08:00
echo.

schtasks /create /tn "%TASK_NAME%" ^
  /tr "python \"%SCRIPT%\"" ^
  /sc weekly /d MON /st 08:00 ^
  /sd %DATE% ^
  /f

IF %ERRORLEVEL% EQU 0 (
    echo.
    echo  SUCCESS! Task created.
    echo  To verify: open Task Scheduler and look for "%TASK_NAME%"
    echo  To run now: schtasks /run /tn "%TASK_NAME%"
) ELSE (
    echo.
    echo  ERROR creating task. Try running this file as Administrator.
)

echo.
pause
