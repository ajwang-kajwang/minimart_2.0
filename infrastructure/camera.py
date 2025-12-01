import cv2
import numpy as np
try:
    from picamera2 import Picamera2
    HAS_PICAMERA2 = True
except ImportError:
    HAS_PICAMERA2 = False
from domain.interfaces import ICameraSource

class CameraService(ICameraSource):
    def __init__(self):
        self.camera = None
        self.use_picamera2 = False
        self._initialize_hardware()

    def _initialize_hardware(self):
        # Logic extracted strictly from yolov8s_tracking_with_coordinates.py
        
        # 1. Try Picamera2 (Preferred)
        if HAS_PICAMERA2:
            try:
                print("   Trying Picamera2...")
                self.camera = Picamera2()
                config = self.camera.create_preview_configuration(
                    main={"size": (1920, 1080), "format": "RGB888"},
                    lores={"size": (1280, 720), "format": "RGB888"}
                )
                self.camera.configure(config)
                self.camera.start()
                
                # Test capture
                if self.camera.capture_array("lores") is not None:
                    self.use_picamera2 = True
                    print("✅ Picamera2 initialized successfully")
                    return
            except Exception as e:
                print(f"   Picamera2 failed: {e}")
                self.release()

        # 2. Fallback to OpenCV
        print("   Trying OpenCV VideoCapture...")
        camera_indices = [0, 1, 2, 3, 10, 11, 12, 13, 14, 15]
        for i in camera_indices:
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        self.camera = cap
                        self.use_picamera2 = False
                        # Set properties
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        self.camera.set(cv2.CAP_PROP_FPS, 30)
                        print(f"✅ OpenCV camera initialized on /dev/video{i}")
                        return
                cap.release()
            except:
                continue
        
        raise Exception("No working camera found")

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        try:
            if self.use_picamera2:
                # Picamera2 returns RGB directly
                return True, self.camera.capture_array("lores")
            else:
                # OpenCV returns BGR, needs conversion
                ret, frame = self.camera.read()
                if ret:
                    return True, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return False, None
        except Exception:
            return False, None

    def release(self):
        if self.camera:
            if self.use_picamera2:
                try: self.camera.stop()
                except: pass
            else:
                self.camera.release()
            self.camera = None