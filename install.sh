#!/bin/bash
set -e

echo "🚀 vLLM Console Installation Starting..."

# 1. Check Dependencies
echo "🔍 Checking dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed."
    exit 1
fi
echo "✅ Python3: $(python3 --version)"

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed."
    exit 1
fi
echo "✅ Node.js: $(node --version)"

# 2. Install Backend
echo ""
echo "📦 Installing backend dependencies..."
cd backend
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q
    echo "✅ Backend dependencies installed."
else
    echo "⚠️ requirements.txt not found."
fi
cd ..

# 3. Install Frontend & Build
echo ""
echo "📦 Installing frontend dependencies..."
cd frontend
if [ -f "package.json" ]; then
    npm install
    echo "✅ Frontend dependencies installed."
    
    echo "🔨 Building frontend..."
    npm run build
    echo "✅ Frontend built successfully."
else
    echo "⚠️ package.json not found."
fi
cd ..

echo ""
echo "✅ Installation complete!"
echo "▶️ Run './start.sh' to start the service."