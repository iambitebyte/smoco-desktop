@echo off
REM ===================================
REM Smoco Desktop - Local Whisper NPU Environment Setup
REM ===================================

echo ===================================
echo   Smoco Desktop - Local Whisper NPU
echo   Environment Setup Script
echo ===================================
echo.

REM Check if uv is installed
uv --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv not found, please install uv first
    echo.
    echo Installation method:
    echo   pip install uv
    echo.
    echo Or visit: https://github.com/astral-sh/uv
    pause
    exit /b 1
)

echo [1/2] Detected uv, version:
uv --version
echo.

echo [2/2] Installing dependencies in whisper-local-npu directory...
echo This may take a few minutes, please wait...
echo.

cd whisper-local-npu

uv sync
if errorlevel 1 (
    echo.
    echo [ERROR] Dependency installation failed
    echo Please check your network connection or try using a mirror:
    echo   set UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
    echo   uv sync
    cd ..
    pause
    exit /b 1
)

cd ..

echo.
echo ===================================
echo   Initialization Complete!
echo ===================================
echo.
echo You can now start SmocoDesktop.exe and use Local Whisper NPU.
echo.

REM Verify installation
if exist "whisper-local-npu\.venv\Scripts\python.exe" (
    echo [OK] Virtual environment created successfully
    whisper-local-npu\.venv\Scripts\python.exe --version
) else (
    echo [WARNING] Virtual environment not found, there may be an issue
)

echo.
pause
