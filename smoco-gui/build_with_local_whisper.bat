@echo off
REM Smoco Desktop Build - Including Local Whisper (完整版，包含 .venv)

echo ===================================
echo   Building with Local Whisper support
echo   This will include the .venv directory (~267MB)
echo ===================================
echo.

REM Check if whisper-local/.venv exists
if not exist "..\whisper-local\.venv\Scripts\python.exe" (
    echo [ERROR] whisper-local/.venv not found or incomplete!
    echo Please run 'uv sync' in whisper-local directory first.
    pause
    exit /b 1
)

REM Disable webrtcvad hook
set HOOK_PATH=.venv\Lib\site-packages\_pyinstaller_hooks_contrib\stdhooks\hook-webrtcvad.py
if exist "%HOOK_PATH%" (
    echo Disabling webrtcvad hook at: %HOOK_PATH%
    move "%HOOK_PATH%" "%HOOK_PATH%.disabled" >nul
    echo Hook disabled successfully
    echo.
)

REM Clean old files
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo Copying whisper-local directory (this may take a while)...
REM Create a temporary copy with only necessary files
if exist "temp_whisper" rmdir /s /q "temp_whisper"
mkdir temp_whisper
xcopy "..\whisper-local\whisper_local_api.py" "temp_whisper\" /Y
xcopy "..\whisper-local\whisper_local_transcriber.py" "temp_whisper\" /Y
xcopy "..\whisper-local\pyproject.toml" "temp_whisper\" /Y

REM Copy .venv (this will take a while)
echo Copying .venv directory (~267MB)...
echo This may take several minutes, please wait...
xcopy "..\whisper-local\.venv" "temp_whisper\.venv\" /E /I /Y

echo Building with Local Whisper support...
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
    --add-data="temp_whisper;whisper-local" ^
    bundle.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    echo Re-enabling webrtcvad hook...
    move "%HOOK_PATH%.disabled" "%HOOK_PATH%" >nul 2>&1
    rmdir /s /q "temp_whisper"
    pause
    exit /b 1
)

REM Re-enable webrtcvad hook
move "%HOOK_PATH%.disabled" "%HOOK_PATH%" >nul 2>&1

REM Clean up temp directory
echo Cleaning up temporary files...
rmdir /s /q "temp_whisper"

echo.
echo ===================================
echo   Build Completed Successfully!
echo ===================================
echo.
echo Output: dist\SmocoDesktop\SmocoDesktop.exe
echo.
echo This build includes Local Whisper support with .venv
echo Total size will be larger (~400MB+)
echo.

dir dist\SmocoDesktop\SmocoDesktop.exe
echo.

echo Testing executable...
start dist\SmocoDesktop\SmocoDesktop.exe

echo.
echo Press any key to open output directory...
pause >nul
explorer dist\SmocoDesktop

echo.
echo If the app runs, Local Whisper should work out of the box!
echo.
