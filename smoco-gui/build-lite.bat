@echo off
REM Smoco Desktop Build - LITE version (Smoco cloud ASR only, NO local whisper)
REM 与 build.bat 的区别：入口 bundle_lite.py（运行时 SMOCO_LITE=1 隐藏 Whisper 设置）、
REM exe 名 SmocoDesktopLite，且不构建/拷贝 whisper-local-npu（主要体积来源）。

echo ===================================
echo   Disabling webrtcvad hook and building LITE
echo ===================================
echo.

REM Find the hook file and disable it（与 build.bat 同理：绕过坏的 contrib hook）
set HOOK_PATH=.venv\Lib\site-packages\_pyinstaller_hooks_contrib\stdhooks\hook-webrtcvad.py
if exist "%HOOK_PATH%" (
    echo Disabling hook at: %HOOK_PATH%
    move "%HOOK_PATH%" "%HOOK_PATH%.disabled" >nul
    echo Hook disabled successfully
) else (
    echo Hook file not found, may already be disabled
)

echo.
echo Building LITE version (no whisper-local-npu)...

REM Clean old files
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

uv run pyinstaller --clean --onedir --noconsole --icon=smoco_logo_circle.ico --name=SmocoDesktopLite ^
    --hidden-import=PyQt6.QtCore --hidden-import=PyQt6.QtGui --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=pyaudiowpatch --hidden-import=numpy --hidden-import=scipy --hidden-import=soundfile ^
    --hidden-import=requests --hidden-import=aiohttp --hidden-import=logging.handlers ^
    --hidden-import=webrtcvad --hidden-import=socketio --hidden-import=engineio ^
    --hidden-import=main_window --hidden-import=gui_logger --hidden-import=i18n --hidden-import=paths ^
    --hidden-import=utils --hidden-import=audio_meter_worker --hidden-import=asr_worker --hidden-import=asr_quality --hidden-import=asr_chunker --hidden-import=smoco_stt_worker ^
    --hidden-import=asr_logger --hidden-import=settings_dialog --hidden-import=startup_dialog ^
    --hidden-import=transcript_edit --hidden-import=local_whisper_manager --hidden-import=translation_worker ^
    --hidden-import=llm_client --hidden-import=smoco.audio --hidden-import=smoco.source.wasapi ^
    --hidden-import=history_page --hidden-import=history_detail_page --hidden-import=log_viewer_page ^
    --hidden-import=history_reader --hidden-import=styles --hidden-import=toast --hidden-import=features ^
    --add-data="smoco_logo_circle.png;." ^
    --add-data="styles.qss;." ^
    --add-data="main_window.py;." --add-data="gui_logger.py;." --add-data="i18n.py;." --add-data="paths.py;." ^
    --add-data="utils.py;." --add-data="audio_meter_worker.py;." --add-data="asr_worker.py;." --add-data="asr_quality.py;." ^
    --add-data="asr_chunker.py;." --add-data="asr_logger.py;." --add-data="smoco_stt_worker.py;." --add-data="settings_dialog.py;." ^
    --add-data="startup_dialog.py;." --add-data="transcript_edit.py;." --add-data="local_whisper_manager.py;." ^
    --add-data="translation_worker.py;." --add-data="llm_client.py;." ^
    --add-data="history_page.py;." --add-data="history_detail_page.py;." ^
    --add-data="history_reader.py;." ^
    --add-data="log_viewer_page.py;." --add-data="styles.py;." --add-data="toast.py;." ^
    --add-data="main.py;." --add-data="bundle_lite.py;." --add-data="features.py;." ^
    bundle_lite.py

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
echo   LITE Build Completed Successfully!
echo ===================================
echo.
echo Output: dist\SmocoDesktopLite\SmocoDesktopLite.exe
echo.
echo NOTE: This is the LITE build - no whisper-local-npu bundled.
echo Whisper settings are hidden at runtime (SMOCO_LITE=1 set by bundle_lite.py).
echo.
echo Distribution size:
powershell -Command "$size = (Get-ChildItem -Recurse 'dist\SmocoDesktopLite' ^| Measure-Object -Property Length -Sum).Sum / 1MB; Write-Host ('{0:N1} MB' -f $size)"
echo.

dir dist\SmocoDesktopLite\SmocoDesktopLite.exe
echo.

echo Testing executable...
start dist\SmocoDesktopLite\SmocoDesktopLite.exe

echo.
echo Press any key to open output directory and re-enable hook...
pause >nul

REM Re-enable the hook
move "%HOOK_PATH%.disabled" "%HOOK_PATH%" >nul 2>&1

explorer dist\SmocoDesktopLite

echo.
echo Hook re-enabled. LITE build done.
echo.
