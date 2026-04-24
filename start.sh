#!/bin/bash
# vLLM Console 启动脚本

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$INSTALL_DIR"

echo -e "\033[0;34m==============================================\033[0m"
echo -e "\033[0;34m  🚀 Starting vLLM Console\033[0m"
echo -e "\033[0;34m==============================================\033[0m"

# 检查端口是否已被占用（使用 lsof 更可靠）
if command -v lsof &>/dev/null && lsof -i :3000 -sTCP:LISTEN &>/dev/null; then
    echo -e "\033[1;33m[!] 端口 3000 已被占用，请先运行 ./stop.sh\033[0m"
    exit 1
elif ! command -v lsof &>/dev/null && ss -tlnp | grep -qE ":[[:space:]]*3000[[:space:]]"; then
    echo -e "\033[1;33m[!] 端口 3000 已被占用，请先运行 ./stop.sh\033[0m"
    exit 1
fi

# 确保数据目录存在
mkdir -p "$INSTALL_DIR/backend/data/db"
mkdir -p "$INSTALL_DIR/backend/data/logs"
mkdir -p "$INSTALL_DIR/logs"

# 启动后端
cd "$INSTALL_DIR/backend"
source venv/bin/activate

nohup uvicorn app.main:app --host 0.0.0.0 --port 3000 > "$INSTALL_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo -e "\033[0;32m[✓] Backend started (PID: $BACKEND_PID)\033[0m"

# 等待后端启动
sleep 3
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo ""
    echo -e "\033[0;34m==============================================\033[0m"
    echo -e "\033[0;32m  🎉 Service started successfully!\033[0m"
    echo -e "\033[0;34m==============================================\033[0m"
    echo ""
    echo -e "  📊 API Docs: \033[0;34mhttp://localhost:3000/docs\033[0m"
    echo -e "  🌐 Frontend: \033[0;34mhttp://localhost:3000\033[0m"
    echo -e "  📝 Backend Log: \033[0;36m$INSTALL_DIR/logs/backend.log\033[0m"
    echo -e "  🛑 Stop: \033[0;36m./stop.sh\033[0m"
    echo ""
else
    echo -e "\033[0;31m[✗] Backend failed to start. Check logs: $INSTALL_DIR/logs/backend.log\033[0m"
    exit 1
fi
