#!/bin/bash
#
# Whisper API 服务器启动脚本
#
# 使用方法：
#   ./start.sh          # 使用默认配置
#   GPU=2 ./start.sh    # 指定 GPU
#   PORT=10060 ./start.sh  # 指定端口

# 激活虚拟环境
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"

# 配置
GPU_ID=${GPU:-2}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}
MODEL_PATH=${MODEL_PATH:-~/models/custom/whisper/medium.pt}

# 启动服务
CUDA_VISIBLE_DEVICES=$GPU_ID python "$SCRIPT_DIR/whisper_api_server.py" \
    --model-path "$MODEL_PATH" \
    --host "$HOST" \
    --port "$PORT"
