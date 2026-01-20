"""
Camera Service - Threaded Reader for Stability
"""
import cv2
import numpy as np
import time
import os
import threading
from typing import Tuple, Optional
from domain.interfaces import ICameraSource

class ThreadedCamera(ICameraSource):
    def __init__(self):
        self.camera_source = os.environ.get('CAMERA_SOURCE', 'rtsp')
        self.stream_url = os.environ.get('CAMERA_STREAM_URL', '')
        self.width = int(os.environ.get('CAMERA_WIDTH', '1280'))
        self.height = int(os.environ.get('CAMERA_HEIGHT', '720'))
        
        # Internal State
        self.cap = None
        self.frame = None
        self.ret = False
        self.running = False
        self.lock = threading.Lock()
        self.thread = None
        self.last_read_time = 0
        
        # Force TCP for stability
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        
        self._initialize_camera()

    def _initialize_camera(self):
        print(f"📷 Initializing Threaded Camera ({self.camera_source})...")
        
        # We stick to CPU/FFmpeg because it handles Auth best.
        # The threading will solve the performance/buffer issues.
        self.cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
        
        if self.cap.isOpened():
            print("   ⏳ Stream opened. Starting capture thread...")
            self.running = True
            self.thread = threading.Thread(target=self._update, daemon=True)
            self.thread.start()
            
            # Wait for first frame
            for _ in range(20):
                if self.ret:
                    print(f"   ✅ Threaded Capture Active!")
                    return
                time.sleep(0.1)
        else:
            print("   ❌ Failed to open stream.")

    def _update(self):
        """
        Background worker that reads frames as fast as possible.
        This keeps the RTSP buffer empty and prevents packet loss errors.
        """
        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            
            if ret:
                with self.lock:
                    self.frame = frame
                    self.ret = ret
                    self.last_read_time = time.time()
            else:
                # If reading fails, wait a bit and try again
                time.sleep(0.1)

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Returns the absolute latest frame instantly.
        Does NOT block waiting for the network.
        """
        if not self.running:
            return False, None

        with self.lock:
            if self.ret and self.frame is not None:
                return True, self.frame.copy()
            
        return False, None
    
    def release(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()

def get_camera_service() -> ICameraSource:
    return ThreadedCamera()