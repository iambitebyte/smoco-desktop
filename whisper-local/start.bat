@echo off
REM Whisper Local API Server Launcher
cd /d "%~dp0"

REM Sync dependencies
echo Syncing dependencies...
call uv sync

REM Select model
echo.
echo =====================================
echo   Whisper Local API Server
echo =====================================
echo.
echo Select Model:
echo   [1] tiny           (Fast, less accurate, ~73M)
echo   [2] base           (Faster, average, ~140M)
echo   [3] small          (Faster, better, ~460M)
echo   [4] medium         (Recommended, balanced, ~1.5G)
echo   [5] large-v3-turbo (Fast and accurate, ~3.3G)
echo   [6] distil-large-v3 (Faster, distilled, ~3.3G)
echo   [7] large-v3       (Most accurate, slow, ~2.9G)
echo.

set /p choice="Select model (1-7): "

REM Map choice to model name
if "%choice%"=="1" set MODEL=tiny
if "%choice%"=="2" set MODEL=base
if "%choice%"=="3" set MODEL=small
if "%choice%"=="4" set MODEL=medium
if "%choice%"=="5" set MODEL=large-v3-turbo
if "%choice%"=="6" set MODEL=distil-large-v3
if "%choice%"=="7" set MODEL=large-v3

REM Default if invalid
if "%MODEL%"=="" set MODEL=medium

echo.
echo Select Language:
echo   [1] Japanese (ja)
echo   [2] Chinese (zh)
echo   [3] English (en)
echo   [4] Korean (ko)
echo   [5] French (fr)
echo   [6] German (de)
echo   [7] Spanish (es)
echo.

set /p lang_choice="Select language (1-7): "

if "%lang_choice%"=="1" set LANG=ja
if "%lang_choice%"=="2" set LANG=zh
if "%lang_choice%"=="3" set LANG=en
if "%lang_choice%"=="4" set LANG=ko
if "%lang_choice%"=="5" set LANG=fr
if "%lang_choice%"=="6" set LANG=de
if "%lang_choice%"=="7" set LANG=es

REM Default if invalid
if "%LANG%"=="" set LANG=ja

echo.
set /p PORT="Enter port (default 8000): "
if "%PORT%"=="" set PORT=8000

echo.
echo =====================================
echo   Configuration
echo =====================================
echo   Model: %MODEL%
echo   Language: %LANG%
echo   Port: %PORT%
echo   Device: CPU
echo   Compute Type: int8
echo =====================================
echo.
echo Loading model (first run will auto-download)...
echo.

REM Start API server
call uv run python whisper_local_api.py --model %MODEL% --language %LANG% --port %PORT%

pause
