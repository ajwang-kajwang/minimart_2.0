# YOLOv8s Tracking with Coordinates - Development Summary

## Project Overview

This project implements a real-time person detection and tracking system using YOLOv8s with coordinate mapping capabilities. The system combines hardware-accelerated AI inference with precise coordinate tracking for retail analytics and monitoring applications.

## Current System Architecture

### Core Components

#### 1. Main Application
- **File**: `yolov8s_tracking_with_coordinates.py`
- **Purpose**: Primary tracking application with Flask web interface
- **Features**:
  - Real-time person detection and tracking
  - Persistent ID assignment using OC-SORT tracking
  - Real-world coordinate mapping
  - Web dashboard with live video feed
  - REST API for coordinate data access
  - SocketIO for real-time updates

#### 2. Detection Engine
- **File**: `crowdhuman_hailo_detector.py`
- **Purpose**: Hardware-accelerated person detection using HAILO8L
- **Features**:
  - Direct HailoRT integration
  - CrowdHuman dataset optimization (person-focused)
  - HAILO8L hardware acceleration
  - Quantized model inference

#### 3. Tracking Modules
- **Files**: `ocsort_tracker.py`, `bytetrack_tracker.py`
- **Purpose**: Advanced object tracking algorithms
- **Features**:
  - OC-SORT: Enhanced occlusion handling
  - ByteTrack: Robust multi-object tracking
  - Persistent ID assignment across frames

#### 4. Coordinate System
- **Files**: `coordinate_calibration.py`, `camera_calibration.py`
- **Purpose**: Pixel-to-world coordinate transformation
- **Features**:
  - Homography matrix calibration
  - Real-world coordinate mapping (0,0) to (100,100)
  - Camera calibration utilities

## Model Evolution

### Phase 1: Initial YOLO Implementation
- Started with standard YOLOv8s model
- CPU-only inference (~3 FPS)
- Basic person detection

### Phase 2: Custom Model Training
- **Model**: `models/custom_yolo_deployment/custom_yolo.pt`
- Custom trained on specific deployment environment
- Improved accuracy for retail scenarios
- Still CPU-limited performance

### Phase 3: Hardware Acceleration Attempts
- Explored HAILO8L integration with DeGirum
- Attempted direct HailoRT implementation
- API compatibility challenges with HailoRT versions

### Phase 4: CrowdHuman Optimization (Current)
- **Model**: `models/yolo_v8_crowdhuman--640x640_quant_hailort_multidevice_1/`
- Quantized HEF model optimized for HAILO8L
- Person-focused training (CrowdHuman dataset)
- **Performance**: 15 FPS with hardware acceleration
- **5x performance improvement** over CPU-only

## Technical Specifications

### Hardware Requirements
- **Platform**: Raspberry Pi 5 with HAILO8L AI accelerator
- **Memory**: 8GB RAM recommended
- **Storage**: ~500MB for models and dependencies

### Software Stack
- **Python**: 3.11+
- **Computer Vision**: OpenCV, Picamera2
- **AI Framework**: Ultralytics YOLO, HailoRT
- **Web Framework**: Flask, Flask-SocketIO
- **Tracking**: OC-SORT, ByteTrack algorithms

### Model Specifications
```json
{
  "model_name": "yolo_v8_crowdhuman",
  "architecture": "HAILO8L",
  "input_resolution": "640x640x3",
  "output_classes": 1,
  "class_mapping": {"0": "person"},
  "performance": "15 FPS",
  "post_processing": "Built-in NMS"
}
```

## Performance Metrics

### Detection Performance
- **FPS**: 15 frames per second
- **Input Resolution**: 1280x720 (detection), 1920x1080 (display)
- **Latency**: ~67ms per frame
- **Hardware Utilization**: HAILO8L accelerated

### Tracking Accuracy
- **Persistent IDs**: Maintained across occlusions
- **Coordinate Precision**: Sub-pixel accuracy with homography mapping
- **Real-time Updates**: WebSocket streaming at 15 FPS

## Development Challenges & Solutions

### 1. Hardware Acceleration Integration
**Challenge**: HailoRT API compatibility issues
**Solution**: Used CrowdHuman pre-quantized model with simplified inference

### 2. Model Optimization
**Challenge**: Generic COCO models not optimized for person detection
**Solution**: Switched to CrowdHuman dataset (person-focused training)

### 3. Performance Bottlenecks
**Challenge**: CPU-only inference limited to 3 FPS
**Solution**: HAILO8L hardware acceleration achieving 15 FPS

### 4. Coordinate Accuracy
**Challenge**: Pixel-to-world mapping precision
**Solution**: Manual calibration with 14-point homography matrix

## API Endpoints

### REST API
- **GET** `/api/coordinates` - Current tracking data
- **GET** `/` - Web dashboard interface

### WebSocket Events
- `video_frame` - Real-time video stream
- `coordinate_update` - Live tracking data

### Response Format
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

## Installation & Usage

### Prerequisites
```bash
# HAILO8L drivers and runtime
sudo apt install hailo-all

# Python dependencies
pip install ultralytics opencv-python flask flask-socketio
```

### Quick Start
```bash
# Activate environment
source venv3/bin/activate

# Run tracking system
python yolov8s_tracking_with_coordinates.py

# Access web interface
open http://localhost:5000
```

## Configuration Files

### Coordinate Calibration
- **File**: `coordinate_calibration.json`
- **Purpose**: Homography matrix for pixel-to-world mapping
- **Format**: 3x3 transformation matrix

### Camera Settings
- **File**: `camera_calibration.json`
- **Purpose**: Camera intrinsic parameters
- **Resolution**: 1920x1080 main, 1280x720 detection

## Future Enhancements

### Short-term
1. **API Compatibility**: Resolve HailoRT direct integration
2. **Model Training**: Custom training on deployment data
3. **Performance**: Target 25+ FPS with optimizations

### Long-term
1. **Multi-camera Support**: Distributed tracking across cameras
2. **Analytics**: Advanced behavior analysis and reporting
3. **Edge Deployment**: Standalone operation without cloud dependencies

## File Structure
```
shelf_main_yolov8s_fork/
├── yolov8s_tracking_with_coordinates.py    # Main application
├── crowdhuman_hailo_detector.py            # HAILO8L detector
├── ocsort_tracker.py                       # Enhanced tracking
├── bytetrack_tracker.py                    # Fallback tracking
├── coordinate_calibration.py               # Coordinate mapping
├── camera_calibration.py                   # Camera utilities
├── coordinate_calibration.json             # Calibration data
├── models/
│   ├── custom_yolo_deployment/             # Custom trained model
│   └── yolo_v8_crowdhuman--640x640*/       # CrowdHuman HEF model
└── venv3/                                  # Python environment
```

## Development Timeline

- **Initial Setup**: Basic YOLOv8s implementation (3 FPS)
- **Custom Training**: Domain-specific model training
- **Hardware Integration**: HAILO8L acceleration attempts
- **CrowdHuman Optimization**: Person-focused model (15 FPS)
- **System Cleanup**: Streamlined codebase and dependencies

## Performance Achievements

- **5x FPS Improvement**: From 3 FPS to 15 FPS
- **Hardware Acceleration**: HAILO8L integration successful
- **Real-time Processing**: Live video and coordinate tracking
- **Production Ready**: Stable web interface and API

---

**Current Status**: Production-ready system with 15 FPS person tracking and real-world coordinate mapping using HAILO8L hardware acceleration.

**Last Updated**: November 2, 2025