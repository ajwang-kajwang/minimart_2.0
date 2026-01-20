# Configuration for Raspberry Pi Camera v3 (IMX708)
export CAMERA_SOURCE=csi
export USE_GSTREAMER=true
export CAMERA_WIDTH=1536
export CAMERA_HEIGHT=864
export CAMERA_FPS=90

# Run the application
echo "🚀 Starting Minimart..."
python3 main.py
EOF