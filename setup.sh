#!/bin/bash
# Minimart 2.0 - Jetson Orin Nano Setup Script
# Run this once after cloning to set up the environment

set -e

echo "=============================================="
echo "Minimart 2.0 - Jetson Orin Nano Setup"
echo "=============================================="

# Check if running on Jetson
if [ -f /etc/nv_tegra_release ]; then
    echo "✅ Jetson platform detected"
    cat /etc/nv_tegra_release
else
    echo "⚠️  Warning: Not running on Jetson hardware"
    echo "   Some features may not work correctly"
fi

# Update system
echo ""
echo "📦 Updating system packages..."
sudo apt-get update

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    libopencv-dev \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly

# Install jetson-stats
echo ""
echo "📊 Installing jetson-stats..."
sudo pip3 install jetson-stats
sudo systemctl restart jtop || true

# Install Python dependencies
echo ""
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements.txt

# Create models directory
echo ""
echo "📁 Creating directories..."
mkdir -p models
mkdir -p logs

# Export TensorRT model (if PyTorch model exists)
if [ -f "yolov8s.pt" ] || command -v python3 &> /dev/null; then
    echo ""
    echo "🔧 Exporting TensorRT model..."
    echo "   This may take 10-20 minutes on first run..."
    python3 scripts/export_tensorrt.py --model yolov8s.pt --output models/yolov8s.engine || {
        echo "⚠️  TensorRT export failed - will use CPU fallback"
    }
fi

# Set up dashboard
echo ""
echo "📊 Setting up dashboard..."
if [ -d "dashboard" ]; then
    cd dashboard
    if command -v npm &> /dev/null; then
        npm install
    else
        echo "⚠️  npm not found - install Node.js to use the dashboard"
    fi
    cd ..
fi

# Performance optimization
echo ""
echo "⚡ Applying performance optimizations..."
sudo nvpmodel -m 0 || echo "   nvpmodel not available"
sudo jetson_clocks || echo "   jetson_clocks not available"

# Done
echo ""
echo "=============================================="
echo "✅ Setup complete!"
echo "=============================================="
echo ""
echo "Quick start:"
echo "  1. Start backend:   python3 main.py"
echo "  2. Start dashboard: cd dashboard && npm run dev"
echo ""
echo "Camera options:"
echo "  USB camera:  CAMERA_SOURCE=usb python3 main.py"
echo "  CSI camera:  CAMERA_SOURCE=csi USE_GSTREAMER=true python3 main.py"
echo "  RTSP stream: CAMERA_SOURCE=rtsp CAMERA_STREAM_URL=rtsp://... python3 main.py"
echo ""
