#!/bin/bash

# 1. Define URL 
URL="rtsp://icp:ICPintern26@192.168.6.38:554/StreamingSetting?version=1.0&action=getRTSPStream&ChannelID=1&ChannelName=Channel1"

echo "=========================================="
echo "DIAGNOSTIC TEST - JETSON CAMERA"
echo "=========================================="

echo "[TEST 1] Pinging Camera..."
ping -c 2 192.168.6.38

echo "\n[TEST 2] GStreamer (uridecodebin) - LIKE LIVESTOCK PROJECT"
# We wrap the URL in quotes so '&' doesn't break it
gst-launch-1.0 uridecodebin uri="$URL" ! fakesink dump=true num-buffers=15
# If this outputs hex data, the new camera.py WILL work.
# If this says "Resource not found", the camera is rejecting the handshake.