#!/bin/bash

# vLLM Console 启动脚本

cd "$(dirname "$0")"

echo "Starting vLLM Console backend..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# 安装依赖（如果未安装）
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
fi

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
