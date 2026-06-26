@echo off
REM Smoco Desktop Build - With whisper-local-npu included

echo ===================================
echo   Disabling webrtcvad hook and building
echo ===================================
echo.

REM Find the hook file and disable it
set HOOK_PATH=.venv\Lib\site-packages\_pyinstaller_hooks_contrib\stdhooks\hook-webrtcvad.py
if exist "%HOOK_PATH%" (
    echo Disabling hook at: %HOOK_PATH%
    move "%HOOK_PATH%" "%HOOK_PATH%.disabled" >nul
    echo Hook disabled successfully
) else (
    echo Hook file not found, may already be disabled
)

echo.
echo Building with whisper-local-npu included...

REM Clean old files
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

uv run pyinstaller --clean --onedir --noconsole --icon=smoco_logo_circle.ico --name=SmocoDesktop ^
    --hidden-import=PyQt6.QtCore --hidden-import=PyQt6.QtGui --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=pyaudiowpatch --hidden-import=numpy --hidden-import=scipy --hidden-import=soundfile ^
    --hidden-import=requests --hidden-import=aiohttp --hidden-import=logging.handlers ^
    --hidden-import=webrtcvad ^
    --hidden-import=main_window --hidden-import=gui_logger --hidden-import=i18n --hidden-import=paths ^
    --hidden-import=utils --hidden-import=audio_meter_worker --hidden-import=asr_worker --hidden-import=asr_chunker ^
    --hidden-import=asr_logger --hidden-import=settings_dialog --hidden-import=startup_dialog ^
    --hidden-import=transcript_edit --hidden-import=local_whisper_manager --hidden-import=translation_worker ^
    --hidden-import=llm_client --hidden-import=smoco.audio --hidden-import=smoco.source.wasapi ^
    --add-data="smoco_logo_circle.png;." ^
    --add-data="main_window.py;." --add-data="gui_logger.py;." --add-data="i18n.py;." --add-data="paths.py;." ^
    --add-data="utils.py;." --add-data="audio_meter_worker.py;." --add-data="asr_worker.py;." ^
    --add-data="asr_chunker.py;." --add-data="asr_logger.py;." --add-data="settings_dialog.py;." ^
    --add-data="startup_dialog.py;." --add-data="transcript_edit.py;." --add-data="local_whisper_manager.py;." ^
    --add-data="translation_worker.py;." --add-data="llm_client.py;." ^
    --add-data="main.py;." --add-data="bundle.py;." ^
    bundle.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    echo Re-enabling webrtcvad hook...
    move "%HOOK_PATH%.disabled" "%HOOK_PATH%" >nul 2>&1
    pause
    exit /b 1
)

echo.
echo ===================================
echo   Copying whisper-local-npu files
echo ===================================

REM Create whisper-local-npu directory in dist
if not exist "dist\SmocoDesktop\whisper-local-npu" mkdir "dist\SmocoDesktop\whisper-local-npu"

REM Copy whisper-local-npu files (excluding .venv)
echo Copying whisper_npu_api.py...
copy "..\whisper-local-npu\whisper_npu_api.py" "dist\SmocoDesktop\whisper-local-npu\" >nul

echo Copying pyproject.toml...
copy "..\whisper-local-npu\pyproject.toml" "dist\SmocoDesktop\whisper-local-npu\" >nul

echo Copying uv.lock...
if exist "..\whisper-local-npu\uv.lock" (
    copy "..\whisper-local-npu\uv.lock" "dist\SmocoDesktop\whisper-local-npu\" >nul
) else (
    echo [WARNING] uv.lock not found, uv sync may take longer
)

REM Copy model files if exists
if exist "..\whisper-local-npu\whisper-small-ov" (
    echo Copying whisper-small-ov model files...
    xcopy "..\whisper-local-npu\whisper-small-ov" "dist\SmocoDesktop\whisper-local-npu\whisper-small-ov\" /E /I /Y >nul
) else (
    echo [WARNING] whisper-small-ov not found, users will need to download models
)

REM Copy init script to root of dist
echo Copying init-whisper-npu.bat...
copy "..\init-whisper-npu.bat" "dist\SmocoDesktop\" >nul

echo.
echo ===================================
echo   Build Completed Successfully!
echo ===================================
echo.
echo Output: dist\SmocoDesktop\SmocoDesktop.exe
echo.
echo whisper-local-npu files:
echo   - dist\SmocoDesktop\whisper-local-npu\*
echo.
echo User setup:
echo   1. Run dist\SmocoDesktop\init-whisper-npu.bat
echo   2. Then start SmocoDesktop.exe
echo.

dir dist\SmocoDesktop\SmocoDesktop.exe
echo.

echo Testing executable...
start dist\SmocoDesktop\SmocoDesktop.exe

echo.
echo Press any key to open output directory and re-enable hook...
pause >nul

REM Re-enable the hook
move "%HOOK_PATH%.disabled" "%HOOK_PATH%" >nul 2>&1

explorer dist\SmocoDesktop

echo.
echo Hook re-enabled. If app runs successfully, we have a working build!
echo.

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    echo Re-enabling webrtcvad hook...
    move "%HOOK_PATH%.disabled" "%HOOK_PATH%" >nul 2>&1
    pause
    exit /b 1
)

REM Clean up temp directory if it exists
if exist "temp_whisper" rmdir /s /q "temp_whisper"

echo.
echo ===================================
echo   Build Completed Successfully!
echo ===================================
echo.
echo Output: dist\SmocoDesktop\SmocoDesktop.exe
echo.

dir dist\SmocoDesktop\SmocoDesktop.exe
echo.

echo Testing executable...
start dist\SmocoDesktop\SmocoDesktop.exe

echo.
echo Press any key to open output directory and re-enable hook...
pause >nul

REM Re-enable the hook
move "%HOOK_PATH%.disabled" "%HOOK_PATH%" >nul 2>&1

explorer dist\SmocoDesktop

echo.
echo Hook re-enabled. If app runs successfully, we have a working build!
echo.
