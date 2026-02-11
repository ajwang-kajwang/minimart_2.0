#!/bin/bash

function cleanup {
    echo ""
    echo "🛑 Shutting down..."
    echo "✅ System stopped."
}

trap cleanup EXIT

echo "🚀 Starting Minimart Pi 5..."

# 2. Wait slightly for system settle
sleep 1

# 3. Launch App
echo "🐍 Launching Orchestrator..."
source venv/bin/activate
python3 main.py