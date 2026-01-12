import cv2
import numpy as np
import time
import os
from typing import Tuple, Optional

from domain.interfaces import ICameraSource

class CameraService(ICameraSource):
    def __init__(self):
        self.camera = None
        
        self.stream_url = os.environ.get('CAMERA_STREAM_URL', 'tcp://127.0.0.1:8888')
        self._initialize_hardware()

    def _initialize_hardware(self):
        print(f"📷 Connecting to Camera Stream at: {self.stream_url}")
        
        for i in range(30):  
            try:
                self.camera = cv2.VideoCapture(self.stream_url)
                if self.camera.isOpened():
                    print("✅ Camera Stream Connected!")
                    return
            except Exception as e:
                print(f"   Connection attempt {i+1} failed: {e}")
            
            time.sleep(2)
        
        print("❌ Failed to connect to camera stream. (Is rpi-stream service running?)")

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.camera or not self.camera.isOpened():
            # Try to reconnect if stream dropped
            self._initialize_hardware()
            if not self.camera or not self.camera.isOpened():
                return False, None

        ret, frame = self.camera.read()
        if ret:
            # frame is already BGR from OpenCV, no conversion needed if source is raw
            return True, frame
        else:
            return False, None

    def release(self):
        if self.camera:
            self.camera.release()