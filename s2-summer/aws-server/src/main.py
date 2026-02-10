# Author: Brian Ngo 10/11/2025
# Email: ngbao128@gmail.com
#!/usr/bin/env python3
"""
Simple IoT Client Entry Point
"""

import threading
import time
from sensor import SensorDataHandler
from camera import CameraDataHandler

def run_sensor():
    """Run sensor handler in a separate thread."""
    print("🌡️  Starting sensor handler...")
    sensor_handler = SensorDataHandler()
    return sensor_handler.run()

def run_camera():
    """Run camera handler in a separate thread."""
    print("📷 Starting camera handler...")
    camera_handler = CameraDataHandler()
    return camera_handler.run()

def main():
    """Main function to run both sensor and camera handlers."""
    print("🚀 Starting IoT client with both sensor and camera handlers...")
    
    # Create threads for both handlers
    sensor_thread = threading.Thread(target=run_sensor, name="SensorThread")
    camera_thread = threading.Thread(target=run_camera, name="CameraThread")
    
    # Start both threads
    sensor_thread.start()
    camera_thread.start()
    
    try:
        # Keep main thread alive
        # while camera_thread.is_alive():
        while sensor_thread.is_alive() or camera_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down both handlers...")
    
    # Wait for threads to complete
    sensor_thread.join(timeout=5)
    camera_thread.join(timeout=5)
    
    print("✅ All handlers stopped")
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)