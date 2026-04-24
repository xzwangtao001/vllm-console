#!/bin/bash
set -e

# =====================================================
# vLLM Console 一键安装脚本
# 用法: bash -c "$(curl -fsSL https://raw.githubusercontent.com/xzwangtao001/vllm-console/main/install.sh)"
# 或: sudo ./install.sh [安装目录]
# =====================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

INSTALL_DIR="${1:-/opt/vllm-console}"
REPO_URL="https://github.com/xzwangtao001/vllm-console.git"
ENABLE_SYSTEMD="${ENABLE_SYSTEMD:-auto}"  # auto/yes/no
VLLM_VERSION="${VLLM_VERSION:-0.19.1}"

# 解析命令行参数
for arg in "$@"; do
    case $arg in
        --systemd) ENABLE_SYSTEMD="yes" ;;
        --no-systemd) ENABLE_SYSTEMD="no" ;;
        --install-dir=*) INSTALL_DIR="${arg#*=}" ;;
        --vllm-version=*) VLLM_VERSION="${arg#*=}" ;;
        --ssh) USE_SSH="yes" ;;
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
    
    log_info "正在从 GitHub 获取项目代码..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    
    # 检测 SSH 克隆方式
    if [ "$USE_SSH" = "yes" ]; then
        log_info "使用 SSH 协议克隆..."
        git clone "git@github.com:xzwangtao001/vllm-console.git" "$INSTALL_DIR" 2>&1 | tail -3
    else
        # 尝试 HTTPS 克隆
        if ! git clone "$REPO_URL" "$INSTALL_DIR" 2>&1 | tail -3; then
            log_warn "HTTPS 克隆失败，尝试下载压缩包..."
            rm -rf "$INSTALL_DIR"
            TMP_ZIP="/tmp/vllm-console-$(date +%s).zip"
            curl -fsSL -o "$TMP_ZIP" "https://github.com/xzwangtao001/vllm-console/archive/refs/heads/main.zip" || {
                log_error "下载失败，请检查网络连接或配置代理"
                log_info "设置代理示例: export https_proxy=http://127.0.0.1:7890"
                exit 1
            }
            mkdir -p "$INSTALL_DIR"
            unzip -q "$TMP_ZIP" -d /tmp/vllm-extract
            mv /tmp/vllm-extract/vllm-console-main/* "$INSTALL_DIR"/
            mv /tmp/vllm-extract/vllm-console-main/.gitignore "$INSTALL_DIR"/ 2>/dev/null || true
            rm -rf "$TMP_ZIP" /tmp/vllm-extract
            log_ok "压缩包解压完成"
        fi
    fi
    log_ok "代码获取完成"
fi

# -------------------------------------------------------
# 3. 安装后端依赖（虚拟环境）
# -------------------------------------------------------
echo ""
log_info "安装后端依赖..."
cd "$INSTALL_DIR/backend"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    log_ok "Python 虚拟环境创建完成"
fi

source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
log_ok "后端依赖安装完成"

# -------------------------------------------------------
# 4. 安装 vLLM 引擎（一次性安装，版本固定）
# -------------------------------------------------------
echo ""
log_info "安装 vLLM 引擎 (v$VLLM_VERSION)..."

# 检测环境选择正确的 vLLM 版本
if nvidia-smi &> /dev/null; then
    # NVIDIA GPU - 检查 CUDA 版本
    CUDA_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1 | awk -F. '{print $1}' || echo "12")
    log_info "检测到 NVIDIA GPU，CUDA 驱动版本: $CUDA_VERSION"
    CUDA_MAJOR=$(echo "$CUDA_VERSION" | head -c 2)
    
    # 安装 vLLM（CPU 模式跳过）
    pip install "vllm==$VLLM_VERSION" -q 2>&1 | tail -5
    log_ok "vLLM $VLLM_VERSION 安装完成"
    
    # 显示版本信息
    VLLM_ACTUAL=$(pip show vllm 2>/dev/null | grep "^Version:" | awk '{print $2}')
    TORCH_VERSION=$(pip show torch 2>/dev/null | grep "^Version:" | awk '{print $2}')
    log_ok "vLLM: $VLLM_ACTUAL | torch: $TORCH_VERSION"
    
    # GPU 信息
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
    GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -1)
    log_ok "GPU: $GPU_NAME ($GPU_MEM)"
    
elif command -v rocm-smi &> /dev/null; then
    log_warn "AMD ROCm 环境 - vLLM ROCm 支持需要额外配置"
    log_info "建议参考: https://docs.vllm.ai/en/latest/getting_started/amd-installation.html"
else
    log_info "未检测到 GPU，安装 CPU 版本 vLLM..."
    pip install "vllm==$VLLM_VERSION" -q 2>&1 | tail -5
    log_ok "vLLM CPU 版本安装完成"
fi

# -------------------------------------------------------
# 5. 安装前端并构建
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
# 6. 创建日志目录
# -------------------------------------------------------
mkdir -p "$INSTALL_DIR/logs"
log_ok "日志目录: $INSTALL_DIR/logs"

# -------------------------------------------------------
# 7. 配置服务启动脚本
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

# 检查端口是否已被占用（使用 lsof，WSL2 兼容）
if command -v lsof &> /dev/null && lsof -i :3000 -sTCP:LISTEN > /dev/null 2>&1; then
    echo -e "\033[1;33m[!] 端口 3000 已被占用，请先运行 ./stop.sh\033[0m"
    lsof -i :3000 -sTCP:LISTEN
    exit 1
elif command -v ss &> /dev/null && ss -tlnp 2>/dev/null | grep -q ":3000 "; then
    # 降级方案：lsof 不可用时用 ss
    echo -e "\033[1;33m[!] 端口 3000 可能被占用\033[0m"
    exit 1
fi

# 启动后端
cd "$INSTALL_DIR/backend"
source venv/bin/activate

nohup uvicorn app.main:app --host 0.0.0.0 --port 3000 > "$INSTALL_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo -e "\033[0;32m[✓] Backend started (PID: $BACKEND_PID)\033[0m"

# 等待后端启动
sleep 3
if curl -sf http://localhost:3000/health > /dev/null 2>&1; then
    echo ""
    echo -e "\033[0;34m==============================================\033[0m"
    echo -e "\033[0;32m  🎉 Service started successfully!\033[0m"
    echo -e "\033[0;34m==============================================\033[0m"
    echo ""
    # 获取本机 IP
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
    echo -e "  🌐 Frontend: \033[0;34mhttp://$LOCAL_IP:3000\033[0m"
    echo -e "  📊 API Docs: \033[0;34mhttp://$LOCAL_IP:3000/docs\033[0m"
    echo -e "  📝 Backend Log: \033[0;36m$INSTALL_DIR/logs/backend.log\033[0m"
    echo -e "  🛑 Stop: \033[0;36m./stop.sh\033[0m"
    echo ""
else
    echo -e "\033[0;31m[✗] Backend failed to start. Check logs: $INSTALL_DIR/logs/backend.log\033[0m"
    cat "$INSTALL_DIR/logs/backend.log" | tail -20
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
# 8. 创建 systemd 服务（可选）
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
