@echo off
REM Smoco Desktop Launcher
cd /d "%~dp0"

echo Starting Smoco...
echo.

uv run smoco run --wasapi --whisper-url http://43.82.132.240:10060 --whisper-lang ja

pause
