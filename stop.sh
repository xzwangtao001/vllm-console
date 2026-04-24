#!/bin/bash
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "\033[0;34m🛑 Stopping vLLM Console...\033[0m"

# 停止后端
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    pkill -f "uvicorn app.main:app"
    echo -e "\033[0;32m[✓] Backend stopped\033[0m"
else
    echo -e "\033[1;33m[!] Backend not running\033[0m"
fi

# 停止前端开发服务器
if pgrep -f "vite" > /dev/null; then
    pkill -f "vite"
    echo -e "\033[0;32m[✓] Frontend stopped\033[0m"
fi

echo -e "\033[0;34m✅ All services stopped\033[0m"
