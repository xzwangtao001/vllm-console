#!/bin/bash
# =====================================================
# vLLM Console 一键下载安装脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/xzwangtao001/vllm-console/main/setup.sh | sudo bash
# =====================================================

SCRIPT_URL="https://raw.githubusercontent.com/xzwangtao001/vllm-console/main/install.sh"

echo "🚀 正在下载安装脚本..."

if command -v curl &> /dev/null; then
    INSTALL_SCRIPT=$(curl -fsSL "$SCRIPT_URL")
elif command -v wget &> /dev/null; then
    INSTALL_SCRIPT=$(wget -qO- "$SCRIPT_URL")
else
    echo "❌ 需要 curl 或 wget"
    exit 1
fi

echo "$INSTALL_SCRIPT" | sudo bash -s "${1:-/opt/vllm-console}"
