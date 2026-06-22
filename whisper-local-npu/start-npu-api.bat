@echo off
REM Whisper 本地 NPU API 服务器启动脚本

cd /d "%~dp0"

echo 正在同步依赖...
call uv sync

echo.
echo 启动 Whisper 本地 NPU API 服务器（交互式配置）...
echo 提示：首次会为 NPU 编译模型，可能耗时较长。
echo.
call uv run python whisper_npu_api.py --interactive

pause
