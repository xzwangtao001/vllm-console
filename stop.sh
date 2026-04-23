#!/bin/bash

echo "🛑 Stopping vLLM Console..."

# 1. Kill Backend
pkill -f "uvicorn app.main"
echo "✅ Backend stopped."

# 2. Kill Frontend (if running in background)
pkill -f "vite"
echo "✅ Frontend stopped."

echo "✅ All services stopped."