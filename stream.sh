#!/bin/bash

# 1. Force Network Mode
export CAMERA_SOURCE=rtsp

# 2. Cisco 7070 Specific URL
# Note: We quote the URL to protect the '&' characters
export CAMERA_STREAM_URL="rtsp://icp:ICPintern26@192.168.6.38:554/StreamingSetting?version=1.0&action=getRTSPStream&ChannelID=1&ChannelName=Channel1"

# 3. Enable GStreamer for Hardware Acceleration
export USE_GSTREAMER=true

# 4. Settings
export CAMERA_WIDTH=1280
export CAMERA_HEIGHT=720
export CAMERA_FPS=30

echo "🚀 Starting Minimart"
python3 main.py