import cv2
import numpy as np
import subprocess
import threading
import time
from domain.interfaces import ICameraSource

class CameraService(ICameraSource):
    def __init__(self):
        self.process = None
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        
        # Resolution configuration
        self.width = 640
        self.height = 640
        # YUV420 frame size = Width * Height * 1.5 bytes
        self.frame_size = int(self.width * self.height * 1.5)
        
        self._initialize_hardware()

    def _initialize_hardware(self):
        print(f"📷 Initializing Direct Pipe to Camera Hardware...")
        
        # Determine the correct command (Pi 5 uses rpicam-vid, older uses libcamera-vid)
        executable = "rpicam-vid"
        try:
            subprocess.run([executable, "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            executable = "libcamera-vid"
            
        print(f"   > Using native tool: {executable}")

        # The Command: Record YUV420 raw video to stdout (-)
        cmd = [
            executable,
            "--timeout", "0",        # Run forever
            "--codec", "yuv420",     # Raw YUV (Fastest)
            "--width", str(self.width),
            "--height", str(self.height),
            "--framerate", "30",
            "--nopreview",           # No HDMI output
            "--vflip",               # Vertical Flip (Hardware)
            "--hflip",               # Horizontal Flip (Hardware)
            "-o", "-"                # Output to stdout
        ]
        
        try:
            # Spawn the process
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.DEVNULL, 
                bufsize=self.frame_size * 2
            )
            self.running = True
            
            # Start a background thread to read the pipe constantly
            self.thread = threading.Thread(target=self._reader_loop, daemon=True)
            self.thread.start()
            
            # Wait up to 5 seconds for the first frame
            for _ in range(50):
                if self.frame is not None:
                    print("✅ Camera Connected (Native Pipe)")
                    return
                time.sleep(0.1)
                
            print("⚠️ Camera process started, but no frames received yet...")
            
        except Exception as e:
            print(f"❌ Failed to start camera process: {e}")

    def _reader_loop(self):
        """Constantly reads raw bytes from the camera process"""
        while self.running and self.process.poll() is None:
            # Read exactly one frame worth of bytes
            raw_bytes = self.process.stdout.read(self.frame_size)
            
            if len(raw_bytes) != self.frame_size:
                continue
                
            # Convert Raw YUV420 -> BGR (for OpenCV)
            try:
                yuv = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((int(self.height * 1.5), self.width))
                bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
                
                with self.lock:
                    self.frame = bgr
            except Exception:
                continue

    def get_frame(self):
        with self.lock:
            if self.frame is not None:
                return True, self.frame.copy()
        return False, None

    def release(self):
        self.running = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()