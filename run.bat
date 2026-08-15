@echo off
REM Double-click launcher for the Microsoft Rewards collector.
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo Python was not found on this PC.
    echo Install it from https://www.python.org/downloads/
    echo Remember to tick "Add python.exe to PATH" during setup.
    echo.
    pause
    exit /b 1
)

python ms_rewards_collector.py
pause
