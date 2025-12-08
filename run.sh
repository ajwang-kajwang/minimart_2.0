#!/bin/bash

# 1. Define a cleanup function
function cleanup {
    echo ""
    echo "🛑 Shutting down hardware services..."
    sudo systemctl stop rpi-stream
    sudo systemctl stop hailo-sidecar
    echo "✅ System stopped."
}

# 2. Set the trap: Run 'cleanup' if the script exits or user hits Ctrl+C
trap cleanup EXIT

echo "🚀 Starting Minimart Hardware Stack..."

# 3. Start the Sidecars
echo "   > Starting Camera Stream..."
sudo systemctl start rpi-stream

echo "   > Starting Hailo AI Server..."
sudo systemctl start hailo-sidecar

# 4. Wait a moment for them to initialize
echo "⏳ Waiting 5 seconds for hardware to warm up..."
sleep 5

# 5. Launch the Main Application (Docker)
echo "🐳 Launching Application..."
docker compose up

# (When you press Ctrl+C in Docker, the script continues to the 'trap' function above)
