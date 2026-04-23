# vLLM Console

🚀 轻量级 vLLM 可视化管理控制台 (MVP)

基于 Python + FastAPI 和 Vue 3 构建的单机版管理后台，支持 Linux 和 Windows WSL 环境。

## 核心功能

- **环境管理**: 自动检测 NVIDIA (CUDA) / AMD (ROCm) GPU 状态及依赖完整性。
- **模型管理**: 支持 HuggingFace / ModelScope 模型元数据拉取、分析与下载。
- **实例控制**: 一键启停 vLLM 实例，支持热重启与进程健康检查。
- **任务中心**: 统一异步任务队列（下载/安装），带进度跟踪与日志查看。
- **资源监控**: 实时查看 GPU 显存、利用率及系统负载。

## 技术栈

- **后端**: Python + FastAPI + SQLAlchemy + SQLite + Psutil
- **前端**: Vue 3 + Element Plus + Pinia + TypeScript
- **部署**: Shell 脚本自动化管理

## 快速开始

### 1. 环境要求
- Python 3.11+
- Node.js 18+
- (可选) NVIDIA GPU 或 AMD ROCm 环境

### 2. 安装
```bash
# 赋予权限
chmod +x install.sh start.sh stop.sh

# 执行安装（会自动安装前后端依赖并构建前端）
./install.sh
```

### 3. 启动服务
```bash
./start.sh
```

### 4. 访问界面
- **API 文档**: http://localhost:3000/docs
- **前端界面**: http://localhost:3000 (生产模式) / http://localhost:3001 (开发模式)

### 5. 停止服务
```bash
./stop.sh
```

## 目录结构

```text
vllm-console/
├── backend/
│   ├── app/            # 核心业务逻辑
│   │   ├── api/        # 路由与 API 接口
│   │   ├── core/       # 配置与数据库
│   │   ├── models/     # SQLAlchemy 数据模型
│   │   ├── services/   # 业务服务层 (Env/Model/Instance/Task)
│   │   └── main.py     # FastAPI 入口
│   ├── data/           # SQLite 数据库文件与日志
│   └── requirements.txt
├── frontend/
│   ├── src/            # Vue 3 源码
│   │   ├── api/        # Axios 封装
│   │   ├── stores/     # Pinia 状态管理
│   │   └── views/      # 页面组件
│   └── package.json
├── install.sh          # 安装脚本
├── start.sh            # 启动脚本
├── stop.sh             # 停止脚本
└── README.md
```

## 开发说明

### 后端开发
```bash
cd backend
uvicorn app.main:app --reload --port 3000
```

### 前端开发
```bash
cd frontend
npm run dev
```

## 已知限制 (MVP)
- 仅支持单机管理，暂不支持多节点集群。
- 数据库使用 SQLite，适合轻量级部署。
- 暂无用户权限控制系统。

---
*Powered by FastAPI & Vue 3*