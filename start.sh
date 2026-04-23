#!/bin/bash

echo "🚀 Starting vLLM Console..."

# 1. Start Backend
echo "🖥 Starting backend on port 3000..."
cd backend
if command -v uvicorn &> /dev/null; then
    nohup uvicorn app.main:app --host 0.0.0.0 --port 3000 > ../logs/backend.log 2>&1 &
    echo "✅ Backend started (PID: $!). Logs: logs/backend.log"
else
    echo "❌ uvicorn not found. Please run install.sh first."
    exit 1
fi
cd ..

# 2. Frontend (Development vs Production)
# For production, usually we serve static files.
# For this MVP, we assume the backend serves the API.
# If frontend is needed in dev mode:
# cd frontend && npm run dev &

echo ""
echo "🎉 Service started!"
echo "🌐 API: http://localhost:3000/docs"
echo "🛑 Run './stop.sh' to stop."