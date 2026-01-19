"""
Camera Service - GStreamer/OpenCV abstraction for Jetson Orin Nano
Supports CSI cameras, USB cameras, and RTSP streams with hardware acceleration
"""

import cv2
import numpy as np
import time
import os
from typing import Tuple, Optional

from domain.interfaces import ICameraSource


class CameraService(ICameraSource):
    """
    Camera abstraction supporting multiple input sources:
    - USB webcam (V4L2)
    - CSI camera (nvarguscamerasrc)
    - RTSP/HTTP streams
    - TCP streams (legacy RP5 compatibility)
    """
    
    def __init__(self):
        self.camera = None
        self.use_gstreamer = os.environ.get('USE_GSTREAMER', 'false').lower() == 'true'
        self.camera_source = os.environ.get('CAMERA_SOURCE', 'usb')  # usb, csi, rtsp, tcp
        self.stream_url = os.environ.get('CAMERA_STREAM_URL', '/dev/video0')
        
        # Frame dimensions (can be overridden)
        self.width = int(os.environ.get('CAMERA_WIDTH', '1280'))
        self.height = int(os.environ.get('CAMERA_HEIGHT', '720'))
        self.fps = int(os.environ.get('CAMERA_FPS', '30'))
        
        self._initialize_camera()
    
    def _get_gstreamer_pipeline(self) -> str:
        """Generate GStreamer pipeline string based on source type"""
        
        if self.camera_source == 'csi':
            # CSI camera (Raspberry Pi Camera v2, IMX219, etc.)
            # Uses nvarguscamerasrc for hardware acceleration
            return (
                f"nvarguscamerasrc sensor-id=0 ! "
                f"video/x-raw(memory:NVMM), width={self.width}, height={self.height}, "
                f"format=NV12, framerate={self.fps}/1 ! "
                f"nvvidconv flip-method=0 ! "
                f"video/x-raw, width={self.width}, height={self.height}, format=BGRx ! "
                f"videoconvert ! "
                f"video/x-raw, format=BGR ! "
                f"appsink drop=1"
            )
        
        elif self.camera_source == 'usb':
            # USB camera with V4L2
            device = self.stream_url if self.stream_url.startswith('/dev/') else '/dev/video0'
            return (
                f"v4l2src device={device} ! "
                f"video/x-raw, width={self.width}, height={self.height}, framerate={self.fps}/1 ! "
                f"videoconvert ! "
                f"video/x-raw, format=BGR ! "
                f"appsink drop=1"
            )
        
        elif self.camera_source == 'rtsp':
            # RTSP/HTTP stream with hardware decoding
            return (
                f"uridecodebin uri={self.stream_url} ! "
                f"nvvidconv ! "
                f"video/x-raw, format=BGRx ! "
                f"videoconvert ! "
                f"video/x-raw, format=BGR ! "
                f"appsink drop=1"
            )
        
        elif self.camera_source == 'tcp':
            # TCP stream (legacy RP5 compatibility)
            return (
                f"tcpclientsrc host={self._parse_tcp_host()} port={self._parse_tcp_port()} ! "
                f"jpegdec ! "
                f"videoconvert ! "
                f"video/x-raw, format=BGR ! "
                f"appsink drop=1"
            )
        
        else:
            raise ValueError(f"Unknown camera source: {self.camera_source}")
    
    def _parse_tcp_host(self) -> str:
        """Extract host from tcp://host:port URL"""
        url = self.stream_url.replace('tcp://', '')
        return url.split(':')[0] if ':' in url else url
    
    def _parse_tcp_port(self) -> int:
        """Extract port from tcp://host:port URL"""
        url = self.stream_url.replace('tcp://', '')
        return int(url.split(':')[1]) if ':' in url else 8888
    
    def _initialize_camera(self):
        """Initialize camera with the appropriate backend"""
        
        print(f"📷 Initializing camera:")
        print(f"   Source: {self.camera_source}")
        print(f"   URL/Device: {self.stream_url}")
        print(f"   Resolution: {self.width}x{self.height}@{self.fps}fps")
        print(f"   GStreamer: {self.use_gstreamer}")
        
        for attempt in range(10):
            try:
                if self.use_gstreamer:
                    # GStreamer pipeline
                    pipeline = self._get_gstreamer_pipeline()
                    print(f"   Pipeline: {pipeline[:80]}...")
                    self.camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
                
                elif self.camera_source == 'usb':
                    # Direct V4L2 access
                    device = self.stream_url if self.stream_url.startswith('/dev/') else '/dev/video0'
                    device_id = int(device.replace('/dev/video', ''))
                    self.camera = cv2.VideoCapture(device_id, cv2.CAP_V4L2)
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.camera.set(cv2.CAP_PROP_FPS, self.fps)
                    self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
                
                elif self.camera_source in ('rtsp', 'tcp'):
                    # OpenCV stream
                    self.camera = cv2.VideoCapture(self.stream_url)
                    self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                elif self.camera_source == 'csi':
                    # CSI requires GStreamer
                    print("   ⚠️  CSI camera requires GStreamer. Enabling...")
                    self.use_gstreamer = True
                    pipeline = self._get_gstreamer_pipeline()
                    self.camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
                
                if self.camera and self.camera.isOpened():
                    # Read test frame
                    ret, frame = self.camera.read()
                    if ret and frame is not None:
                        actual_h, actual_w = frame.shape[:2]
                        print(f"✅ Camera connected! Actual resolution: {actual_w}x{actual_h}")
                        return
                    else:
                        print(f"   Attempt {attempt + 1}: Can't read frame")
                else:
                    print(f"   Attempt {attempt + 1}: Failed to open camera")
            
            except Exception as e:
                print(f"   Attempt {attempt + 1} failed: {e}")
            
            time.sleep(2)
        
        print("❌ Failed to initialize camera after 10 attempts")
        print("   Troubleshooting:")
        print("   - For USB: Check 'ls /dev/video*'")
        print("   - For CSI: Run 'nvgstcapture-1.0' to test")
        print("   - For RTSP: Verify stream URL is accessible")
    
    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Capture a single frame"""
        
        if not self.camera or not self.camera.isOpened():
            # Attempt reconnection
            self._initialize_camera()
            if not self.camera or not self.camera.isOpened():
                return False, None
        
        ret, frame = self.camera.read()
        
        if ret and frame is not None:
            return True, frame
        else:
            # Connection may have dropped
            print("⚠️  Frame read failed, attempting reconnect...")
            self._initialize_camera()
            return False, None
    
    def release(self):
        """Release camera resources"""
        if self.camera:
            self.camera.release()
            print("📷 Camera released")


class TestPatternCamera(ICameraSource):
    """
    Generates test pattern frames for development without hardware.
    Useful for testing the pipeline when no camera is available.
    """
    
    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.frame_count = 0
        print(f"🎬 Test pattern camera: {width}x{height}")
    
    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Generate a test frame with moving elements"""
        
        # Create gradient background
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Horizontal gradient
        for x in range(self.width):
            frame[:, x, 0] = int(255 * x / self.width)  # Blue
            frame[:, x, 2] = int(255 * (1 - x / self.width))  # Red
        
        # Moving circle (simulates person)
        cx = int((self.frame_count * 5) % self.width)
        cy = self.height // 2
        cv2.circle(frame, (cx, cy), 50, (0, 255, 0), -1)
        
        # Second moving element
        cx2 = int((self.width - (self.frame_count * 3) % self.width))
        cy2 = self.height // 3
        cv2.circle(frame, (cx2, cy2), 40, (255, 255, 0), -1)
        
        # Frame counter
        cv2.putText(
            frame, f"Frame: {self.frame_count}",
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2
        )
        cv2.putText(
            frame, "TEST PATTERN - No Camera",
            (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2
        )
        
        self.frame_count += 1
        time.sleep(0.033)  # ~30 FPS
        
        return True, frame
    
    def release(self):
        """No resources to release"""
        pass


def get_camera_service() -> ICameraSource:
    """Factory function to get appropriate camera service"""
    
    if os.environ.get('USE_TEST_PATTERN', 'false').lower() == 'true':
        return TestPatternCamera()
    
    return CameraService()
