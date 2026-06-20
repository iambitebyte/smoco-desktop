@echo off
REM Whisper 本地 API 服务器启动脚本

REM 进入脚本目录
cd /d "%~dp0"

REM 同步依赖
echo 正在同步依赖...
call uv sync

REM 启动 API 服务器（交互式配置）
echo.
echo 启动 Whisper 本地 API 服务器...
echo.
call uv run python whisper_local_api.py --interactive

pause
