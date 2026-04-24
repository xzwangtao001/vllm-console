#!/bin/bash
set -e

# =====================================================
# vLLM Console 一键安装脚本
# 用法: bash -c "$(curl -fsSL https://raw.githubusercontent.com/xzwangtao001/vllm-console/main/install.sh)"
# 或: ./install.sh [安装目录]
# =====================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

INSTALL_DIR="${1:-/opt/vllm-console}"
REPO_URL="https://github.com/xzwangtao001/vllm-console.git"
ENABLE_SYSTEMD="${ENABLE_SYSTEMD:-auto}"  # auto/yes/no

# 解析命令行参数
for arg in "$@"; do
    case $arg in
        --systemd) ENABLE_SYSTEMD="yes" ;;
        --no-systemd) ENABLE_SYSTEMD="no" ;;
        --install-dir=*) INSTALL_DIR="${arg#*=}" ;;
    esac
done

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# -------------------------------------------------------
# 检查是否 root
# -------------------------------------------------------
if [ "$(id -u)" -ne 0 ]; then
    log_error "请使用 root 权限运行此脚本: sudo bash install.sh"
    exit 1
fi

echo -e "${BLUE}"
echo "=============================================="
echo "  🚀 vLLM Console 一键安装"
echo "=============================================="
echo -e "${NC}"

# -------------------------------------------------------
# 1. 系统依赖检测与安装
# -------------------------------------------------------
log_info "检查系统依赖..."

install_if_missing() {
    if command -v "$1" &> /dev/null; then
        log_ok "$1 已安装: $($1 --version 2>&1 | head -1)"
    else
        log_warn "$1 未安装，正在安装..."
        if command -v apt-get &> /dev/null; then
            apt-get update -qq && apt-get install -y -qq "$2" 2>&1 | tail -1
        elif command -v yum &> /dev/null; then
            yum install -y "$2" 2>&1 | tail -1
        elif command -v pacman &> /dev/null; then
            pacman -S --noconfirm "$2" 2>&1 | tail -1
        else
            log_error "无法自动安装 $1，请手动安装后重试"
            exit 1
        fi
        log_ok "$1 安装完成: $($1 --version 2>&1 | head -1)"
    fi
}

install_if_missing python3 python3
install_if_missing pip3 python3-pip
install_if_missing node nodejs
install_if_missing npm npm

# 安装 venv（Python虚拟环境依赖）
if python3 -c "import venv" 2>/dev/null; then
    log_ok "python3-venv 已安装"
else
    log_warn "python3-venv 未安装，正在安装..."
    if command -v apt-get &> /dev/null; then
        apt-get update -qq && apt-get install -y -qq python3-venv 2>&1 | tail -1
    elif command -v yum &> /dev/null; then
        yum install -y python3-venv 2>&1 | tail -1
    else
        log_error "无法自动安装 python3-venv，请手动安装: sudo apt install python3-venv"
        exit 1
    fi
    log_ok "python3-venv 安装完成"
fi

# 检查 GPU 驱动（仅提示）
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "unknown")
    log_ok "检测到 NVIDIA GPU: $GPU_INFO"
elif command -v rocm-smi &> /dev/null; then
    log_ok "检测到 AMD ROCm 环境"
else
    log_warn "未检测到 GPU，请确认是否需要 vLLM"
fi

# -------------------------------------------------------
# 2. 获取项目代码
# -------------------------------------------------------
echo ""
log_info "安装目录: $INSTALL_DIR"

if [ -d "$INSTALL_DIR/.git" ]; then
    log_warn "目录已存在，尝试从 GitHub 更新..."
    cd "$INSTALL_DIR"
    git pull origin main 2>/dev/null || log_warn "更新失败，使用现有代码"
    cd - > /dev/null
else
    # 如果目录存在但没有 .git，备份后克隆
    if [ -d "$INSTALL_DIR" ]; then
        BACKUP_DIR="${INSTALL_DIR}.bak.$(date +%s)"
        log_warn "目录已存在，备份到: $BACKUP_DIR"
        mv "$INSTALL_DIR" "$BACKUP_DIR"
    fi
    
    log_info "正在从 GitHub 克隆项目..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone "$REPO_URL" "$INSTALL_DIR"
    log_ok "代码克隆完成"
fi

# -------------------------------------------------------
# 3. 安装后端依赖（虚拟环境）
# -------------------------------------------------------
echo ""
log_info "安装后端依赖..."
cd "$INSTALL_DIR/backend"

if [ ! -f "venv/bin/activate" ]; then
    rm -rf venv
    python3 -m venv venv
    log_ok "Python 虚拟环境创建完成"
fi

source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
log_ok "后端依赖安装完成: $(pip list 2>/dev/null | grep -iE 'fastapi|uvicorn' | tr '\n' ', ')"

# -------------------------------------------------------
# 4. 安装前端并构建
# -------------------------------------------------------
echo ""
log_info "安装前端依赖..."
cd "$INSTALL_DIR/frontend"

npm install --production=false 2>&1 | tail -3
log_ok "前端依赖安装完成"

echo ""
log_info "构建前端..."
npm run build 2>&1 | tail -3
log_ok "前端构建完成"

# -------------------------------------------------------
# 5. 创建日志目录
# -------------------------------------------------------
mkdir -p "$INSTALL_DIR/logs"
log_ok "日志目录: $INSTALL_DIR/logs"

# -------------------------------------------------------
# 6. 配置服务启动脚本
# -------------------------------------------------------
echo ""
log_info "配置启动脚本..."

# 更新 start.sh 中的路径
cat > "$INSTALL_DIR/start.sh" << 'START_EOF'
#!/bin/bash
# vLLM Console 启动脚本

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$INSTALL_DIR"

echo -e "\033[0;34m==============================================\033[0m"
echo -e "\033[0;34m  🚀 Starting vLLM Console\033[0m"
echo -e "\033[0;34m==============================================\033[0m"

# 检查端口是否已被占用
if ss -tlnp | grep -q ":3000 "; then
    echo -e "\033[1;33m[!] 端口 3000 已被占用，请先运行 ./stop.sh\033[0m"
    exit 1
fi

# 启动后端
cd "$INSTALL_DIR/backend"
source venv/bin/activate

nohup uvicorn app.main:app --host 0.0.0.0 --port 3000 > "$INSTALL_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo -e "\033[0;32m[✓] Backend started (PID: $BACKEND_PID)\033[0m"

# 等待后端启动
sleep 2
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo ""
    echo -e "\033[0;34m==============================================\033[0m"
    echo -e "\033[0;32m  🎉 Service started successfully!\033[0m"
    echo -e "\033[0;34m==============================================\033[0m"
    echo ""
    echo -e "  📊 API Docs: \033[0;34mhttp://localhost:3000/docs\033[0m"
    echo -e "  🌐 Frontend: \033[0;34mhttp://localhost:3001\033[0m (dev mode)"
    echo -e "  📝 Backend Log: \033[0;36m$INSTALL_DIR/logs/backend.log\033[0m"
    echo -e "  🛑 Stop: \033[0;36m./stop.sh\033[0m"
    echo ""
else
    echo -e "\033[0;31m[✗] Backend failed to start. Check logs: $INSTALL_DIR/logs/backend.log\033[0m"
    exit 1
fi
START_EOF

# 更新 stop.sh
cat > "$INSTALL_DIR/stop.sh" << 'STOP_EOF'
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
STOP_EOF

chmod +x "$INSTALL_DIR/start.sh" "$INSTALL_DIR/stop.sh"
log_ok "启动脚本配置完成"

# -------------------------------------------------------
# 7. 创建 systemd 服务（可选）
# -------------------------------------------------------
echo ""

# 判断是否启用 systemd: 优先环境变量/参数, 否则检测当前环境
if [ "$ENABLE_SYSTEMD" = "auto" ]; then
    # 默认启用: root + systemd 存在 = 自动开启
    if [ -d /run/systemd/system ]; then
        ENABLE_SYSTEMD="yes"
        log_info "检测到 systemd 环境，自动启用开机自启服务"
    else
        ENABLE_SYSTEMD="no"
        log_info "非 systemd 环境，跳过开机自启"
    fi
fi

if [ "$ENABLE_SYSTEMD" = "yes" ]; then
    cat > /etc/systemd/system/vllm-console.service << SYSTEMD_EOF
[Unit]
Description=vLLM Console
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR/backend
ExecStart=$INSTALL_DIR/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 3000
Restart=always
RestartSec=5
StandardOutput=append:$INSTALL_DIR/logs/backend.log
StandardError=append:$INSTALL_DIR/logs/backend.log

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

    systemctl daemon-reload
    systemctl enable vllm-console
    log_ok "systemd 服务已创建并启用"
    log_info "启动服务: systemctl start vllm-console"
    log_info "查看状态: systemctl status vllm-console"
    log_info "查看日志: journalctl -u vllm-console -f"
else
    log_info "跳过 systemd 服务配置"
fi

# -------------------------------------------------------
# 完成
# -------------------------------------------------------
echo ""
echo -e "${BLUE}=============================================="
echo -e "  ✅ 安装完成!"
echo -e "==============================================${NC}"
echo ""
echo -e "  📂 安装目录: ${GREEN}$INSTALL_DIR${NC}"
echo -e "  🚀 启动服务: ${GREEN}cd $INSTALL_DIR && ./start.sh${NC}"
echo -e "  🛑 停止服务: ${GREEN}./stop.sh${NC}"
echo -e "  📊 API 文档: ${GREEN}http://<your-ip>:3000/docs${NC}"
echo ""
