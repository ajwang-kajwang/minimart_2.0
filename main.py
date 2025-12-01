#!/usr/bin/env python3
"""
Minimart Tracking System - Main Orchestrator
"""

import cv2
import time
import threading
import json
import numpy as np
from flask import Flask, Response, jsonify
from flask_socketio import SocketIO

# Import Domain Interfaces (The Contracts)
from domain.interfaces import ICameraSource, IDetector, ITracker

# Import Concrete Services (The Implementations)
from infrastructure.camera import CameraService
from services.detection import DetectionService
from services.tracking import TrackingService
from services.geometry import GeometryService

# --- Main Application Orchestrator ---
class MinimartTrackerApp:
    def __init__(self, camera: ICameraSource, detector: IDetector, tracker: ITracker, geometry: GeometryService):
        # Dependencies injected via constructor (DIP compliant)
        self.camera = camera
        self.detector = detector
        self.tracker = tracker
        self.geometry = geometry
        
        # Application State
        self.running = False
        self.current_frame = None
        self.tracked_people = []
        self.fps = 0
        self.lock = threading.Lock()
        
        # Web Server Setup
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'minimart_solid_refactor'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return "Minimart Tracking System Active (See /video_feed)"

        @self.app.route('/video_feed')
        def video_feed():
            return Response(self._generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/api/coordinates')
        def api_coordinates():
            with self.lock:
                active = [p for p in self.tracked_people if p['active']]
                return jsonify({
                    'active_count': len(active),
                    'total_tracks': len(self.tracked_people),
                    'fps': self.fps,
                    'people': self.tracked_people
                })

    def _generate_frames(self):
        while True:
            with self.lock:
                if self.current_frame is not None:
                    ret, buffer = cv2.imencode('.jpg', self.current_frame)
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.033)

    def _processing_loop(self):
        print("🔄 Starting processing loop...")
        frame_count = 0
        start_time = time.time()
        last_emit = time.time()

        while self.running:
            # 1. Hardware Access (via Interface)
            success, frame = self.camera.get_frame()
            if not success:
                time.sleep(0.01)
                continue

            # 2. Detection (via Interface)
            detections = self.detector.detect(frame)

            # 3. Tracking (via Interface)
            tracks = self.tracker.update(detections)

            # 4. Coordinate Mapping (via GeometryService)
            for person in tracks:
                cx = person['x'] + person['width'] / 2
                cy = person['y'] + person['height'] / 2
                
                # Delegate math to service
                world_x, world_y = self.geometry.pixel_to_world((cx, cy))
                
                person['center_pixel'] = (cx, cy)
                person['real_world'] = {
                    'x': world_x,
                    'y': world_y
                }

            # 5. Visualization (Presentation Logic)
            annotated_frame = frame.copy()
            for p in tracks:
                x, y, w, h = int(p['x']), int(p['y']), int(p['width']), int(p['height'])
                color = p['color']
                cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), color, 2)
                
                label = f"ID {p['id']}"
                if 'real_world' in p:
                    label += f" ({p['real_world']['x']:.1f}, {p['real_world']['y']:.1f})"
                
                # Draw label background
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(annotated_frame, (x, y-th-10), (x+tw, y), color, -1)
                cv2.putText(annotated_frame, label, (x, y-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)

            # 6. Update State (Thread Safe)
            with self.lock:
                self.current_frame = annotated_frame
                self.tracked_people = tracks
            
            # 7. Metrics & WebSocket
            frame_count += 1
            if time.time() - start_time > 1.0:
                self.fps = frame_count / (time.time() - start_time)
                frame_count = 0
                start_time = time.time()
                print(f"FPS: {self.fps:.1f} | Active: {len([t for t in tracks if t['active']])}")

            if time.time() - last_emit > 0.1: # 100ms emit rate
                with self.lock:
                    # Filter only active people for the API/Socket update
                    active_tracks = [p for p in tracks if p['active']]
                    self.socketio.emit('coordinate_tracking_update', {
                        'active_count': len(active_tracks),
                        'fps': self.fps,
                        'people': tracks
                    })
                last_emit = time.time()

    def start(self):
        self.running = True
        
        # Start Processing Thread
        process_thread = threading.Thread(target=self._processing_loop)
        process_thread.daemon = True
        process_thread.start()
        
        # Start Web Server
        print("Minimart Tracker Started (http://0.0.0.0:5000)")
        try:
            self.socketio.run(self.app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        print("Stopping...")
        self.running = False
        self.camera.release()

if __name__ == "__main__":
    # --- Composition Root ---
    # Classes are instantiated.
    # All services are wired together here and injected into the application.
    
    # 1. Initialize Services
    camera_svc = CameraService()
    detection_svc = DetectionService(confidence_threshold=0.4)
    tracking_svc = TrackingService(max_distance=150)
    geometry_svc = GeometryService(calibration_file="coordinate_calibration.json")

    # 2. Inject Dependencies
    app = MinimartTrackerApp(
        camera=camera_svc,
        detector=detection_svc,
        tracker=tracking_svc,
        geometry=geometry_svc
    )
    
    # 3. Launch Application
    app.start()