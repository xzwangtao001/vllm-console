#!/bin/bash
set -e

# =====================================================
# vLLM Console 局域网一键安装脚本
# 用法: bash -c "$(curl -fsSL http://192.168.110.132:8080/install-local.sh)"
# =====================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="${1:-/opt/vllm-console}"
HTTP_BASE="http://192.168.110.132:8080"
VLLM_VERSION="0.19.1"

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# 检查是否 root
if [ "$(id -u)" -ne 0 ]; then
    log_error "请使用 root 权限运行: sudo bash install-local.sh"
    exit 1
fi

echo -e "${BLUE}=============================================="
echo "  🚀 vLLM Console 局域网安装 (192.168.110.132)"
echo "==============================================${NC}"

# 1. 测试连通性
log_info "测试服务器连通性..."
if ! curl -sf "${HTTP_BASE}/README.md" > /dev/null; then
    log_error "无法连接 ${HTTP_BASE}，请确认服务已启动"
    exit 1
fi
log_ok "服务器连通"

# 2. 下载项目代码
echo ""
log_info "安装目录: $INSTALL_DIR"

if [ -d "$INSTALL_DIR" ]; then
    BACKUP_DIR="${INSTALL_DIR}.bak.$(date +%s)"
    log_warn "目录已存在，备份到: $BACKUP_DIR"
    sudo mv "$INSTALL_DIR" "$BACKUP_DIR"
fi

mkdir -p "$INSTALL_DIR"
TMP_ZIP="/tmp/vllm-console.zip"

log_info "正在下载项目代码..."
curl -fsSL -o "$TMP_ZIP" "${HTTP_BASE}/vllm-console.zip"
python3 -c "
import zipfile
with zipfile.ZipFile('$TMP_ZIP', 'r') as z:
    z.extractall('/tmp/vllm-extract')
"
# 检测是根目录结构还是子目录结构
if [ -d "/tmp/vllm-extract/vllm-console-main" ]; then
    mv /tmp/vllm-extract/vllm-console-main/* "$INSTALL_DIR"/
    mv /tmp/vllm-extract/vllm-console-main/.git* "$INSTALL_DIR"/ 2>/dev/null || true
else
    mv /tmp/vllm-extract/* "$INSTALL_DIR"/
fi
rm -rf "$TMP_ZIP" /tmp/vllm-extract
log_ok "代码下载完成"

# 3. 安装后端依赖
echo ""
log_info "安装后端依赖..."
cd "$INSTALL_DIR/backend"

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -r requirements.txt -q
log_ok "后端依赖安装完成"

# 4. 安装 vLLM
echo ""
log_info "安装 vLLM 引擎 (v$VLLM_VERSION) [使用本地离线包]..."

# 尝试从本地服务下载离线包
WHEEL_URL="${HTTP_BASE}/wheels/vllm-0.19.1-cp38-abi3-manylinux_2_31_x86_64.whl"
LOCAL_WHEEL="/tmp/vllm-local.whl"

if curl -sf "$WHEEL_URL" -o "$LOCAL_WHEEL"; then
    log_info "使用离线 wheel 安装 vLLM (速度更快)"
    pip install --no-deps "$LOCAL_WHEEL"
    log_ok "vLLM 核心包安装完成"
    
    # 补充安装依赖（从清华镜像）
    log_info "正在安装 vLLM 依赖..."
    pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn "vllm[standard]==$VLLM_VERSION" -q 2>&1 | tail -3
else
    log_warn "无法获取离线包，将从网络安装..."
    pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn "vllm==$VLLM_VERSION" 2>&1 | tail -5
fi

rm -f "$LOCAL_WHEEL"
VLLM_ACTUAL=$(pip show vllm 2>/dev/null | grep "^Version:" | awk '{print $2}')
log_ok "vLLM $VLLM_ACTUAL 安装完成"

if nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
    GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -1)
    log_ok "GPU: $GPU_NAME ($GPU_MEM)"
fi

# 5. 安装前端并构建
echo ""
log_info "安装前端依赖..."
cd "$INSTALL_DIR/frontend"
npm install --production=false 2>&1 | tail -3
log_ok "前端依赖安装完成"

log_info "构建前端..."
npm run build 2>&1 | tail -3
log_ok "前端构建完成"

# 6. 配置启动脚本
echo ""
mkdir -p "$INSTALL_DIR/logs"

cat > "$INSTALL_DIR/start.sh" << 'START_EOF'
#!/bin/bash
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$INSTALL_DIR"

echo -e "\033[0;34m==============================================\033[0m"
echo -e "\033[0;34m  🚀 Starting vLLM Console\033[0m"
echo -e "\033[0;34m==============================================\033[0m"

if command -v lsof &> /dev/null && lsof -i :3000 -sTCP:LISTEN > /dev/null 2>&1; then
    echo -e "\033[1;33m[!] 端口 3000 已被占用，请先运行 ./stop.sh\033[0m"
    lsof -i :3000 -sTCP:LISTEN
    exit 1
fi

cd "$INSTALL_DIR/backend"
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 3000 > "$INSTALL_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo -e "\033[0;32m[✓] Backend started (PID: $BACKEND_PID)\033[0m"

sleep 3
if curl -sf http://localhost:3000/health > /dev/null 2>&1; then
    echo ""
    echo -e "\033[0;34m==============================================\033[0m"
    echo -e "\033[0;32m  🎉 Service started successfully!\033[0m"
    echo -e "\033[0;34m==============================================\033[0m"
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
    echo ""
    echo -e "  🌐 Frontend: \033[0;34mhttp://$LOCAL_IP:3000\033[0m"
    echo -e "  📊 API Docs: \033[0;34mhttp://$LOCAL_IP:3000/docs\033[0m"
    echo -e "  📝 Log: \033[0;36m$INSTALL_DIR/logs/backend.log\033[0m"
    echo -e "  🛑 Stop: \033[0;36m./stop.sh\033[0m"
    echo ""
else
    echo -e "\033[0;31m[✗] Backend failed. Check logs: $INSTALL_DIR/logs/backend.log\033[0m"
    tail -20 "$INSTALL_DIR/logs/backend.log"
    exit 1
fi
START_EOF

cat > "$INSTALL_DIR/stop.sh" << 'STOP_EOF'
#!/bin/bash
echo -e "\033[0;34m🛑 Stopping vLLM Console...\033[0m"
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    pkill -f "uvicorn app.main:app"
    echo -e "\033[0;32m[✓] Backend stopped\033[0m"
else
    echo -e "\033[1;33m[!] Backend not running\033[0m"
fi
echo -e "\033[0;34m✅ All services stopped\033[0m"
STOP_EOF

chmod +x "$INSTALL_DIR/start.sh" "$INSTALL_DIR/stop.sh"
log_ok "启动脚本配置完成"

# 完成
echo ""
echo -e "${BLUE}=============================================="
echo "  ✅ 安装完成!"
echo "==============================================${NC}"
echo ""
echo -e "  📂 安装目录: ${GREEN}$INSTALL_DIR${NC}"
echo -e "  🚀 启动: ${GREEN}cd $INSTALL_DIR && ./start.sh${NC}"
echo -e "  🌐 访问: ${GREEN}http://<your-ip>:3000${NC}"
echo ""
