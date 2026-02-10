# YOLOv8s Person Tracking with HAILO8L Hardware Acceleration

Real-time person detection and tracking system optimized for retail environments. Features 15 FPS performance with HAILO8L hardware acceleration, coordinate mapping, and web-based monitoring.

## Features

- 🎯 **Real-time Person Tracking**: 15 FPS with persistent ID assignment
- ⚡ **HAILO8L Acceleration**: Hardware-optimized inference using CrowdHuman model
- 🗺️ **Coordinate Mapping**: Pixel-to-world coordinate transformation
- 📊 **Web Dashboard**: Live video feed and analytics interface
- 🔌 **REST API**: Real-time coordinate data access
- 📱 **WebSocket Support**: Live streaming updates

## Quick Start

### Option 1: Automated Installation
```bash
# Clone repository
git clone https://github.com/Quakerz17/minimart_tracking_yolov8.git
cd minimart_tracking_yolov8

# Run automated installer
python3 install_dependencies.py
```

### Option 2: Quick Setup (Essential packages only)
```bash
# Quick installation of core dependencies
python3 quick_setup.py

# Or install manually
pip install -r requirements.txt
```

### Option 3: Manual Installation
```bash
# Install system dependencies (Raspberry Pi)
sudo apt update
sudo apt install -y hailo-all libcamera-apps python3-picamera2

# Install Python dependencies
pip install ultralytics opencv-python flask flask-socketio numpy scipy picamera2
```

## Usage

```bash
# Start the tracking system
python yolov8s_tracking_with_coordinates.py

# Access web interface
open http://localhost:5000

# API endpoint for coordinate data
curl http://localhost:5000/api/coordinates
```

## System Requirements

- **Hardware**: Raspberry Pi 5 with HAILO8L AI accelerator
- **OS**: Raspberry Pi OS (64-bit) or compatible Linux
- **Python**: 3.11+
- **Memory**: 4GB+ RAM recommended
- **Camera**: Compatible with libcamera/Picamera2

## Performance

- **Detection Speed**: 15 FPS (HAILO8L) vs 3 FPS (CPU-only)
- **Accuracy**: Person-focused CrowdHuman model optimization
- **Latency**: ~67ms per frame
- **Resolution**: 1920x1080 display, 1280x720 detection

## Model Information

The system uses two model options:
1. **CrowdHuman YOLO v8** (Primary): Hardware-accelerated HEF model for HAILO8L
2. **Custom YOLO v8** (Fallback): Custom-trained model for specific environments

## API Response Format

```json
{
  "active_count": 2,
  "fps": 15.0,
  "people": [
    {
      "id": 1,
      "bbox": [x1, y1, x2, y2],
      "confidence": 0.85,
      "coordinates": [45.2, 67.8]
    }
  ]
}
```

## Documentation

See [DEVELOPMENT_SUMMARY.md](DEVELOPMENT_SUMMARY.md) for detailed technical documentation and development history.

## License

MIT License - see repository for details.
This repo contains all the python files and models used for the development of the software.
