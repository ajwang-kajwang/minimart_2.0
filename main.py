#!/usr/bin/env python3
"""
Minimart Tracking System - Jetson Orin Nano Edition
Main Application Orchestrator
"""

import cv2
import time
import threading
import numpy as np
from flask import Flask, Response, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

# Import Domain Interfaces
from domain.interfaces import ICameraSource, IDetector, ITracker

# Import Concrete Services
from infrastructure.camera import CameraService, get_camera_service
from services.detection import DetectionService
from services.tracking import TrackingService
from services.geometry import GeometryService
from services.telemetry import get_telemetry_service


class MinimartTrackerApp:
    """Main application orchestrating all services"""
    
    def __init__(
        self,
        camera: ICameraSource,
        detector: IDetector,
        tracker: ITracker,
        geometry: GeometryService
    ):
        # Dependencies injected via constructor (DIP compliant)
        self.camera = camera
        self.detector = detector
        self.tracker = tracker
        self.geometry = geometry
        self.telemetry = get_telemetry_service()
        
        # Application State
        self.running = False
        self.current_frame = None
        self.tracked_people = []
        self.fps = 0
        self.inference_time_ms = 0
        self.lock = threading.Lock()
        
        # Session statistics
        self.session_start = time.time()
        self.total_frames = 0
        self.total_detections = 0
        
        # Web Server Setup
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'minimart_jetson_v2'
        CORS(self.app)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')
        
        self._setup_routes()
        self._setup_socket_events()
    
    def _setup_routes(self):
        """Configure Flask routes"""
        
        @self.app.route('/')
        def index():
            return jsonify({
                'service': 'Minimart Tracking System',
                'platform': 'Jetson Orin Nano',
                'version': '2.0.0',
                'endpoints': {
                    'video_feed': '/video_feed',
                    'coordinates': '/api/coordinates',
                    'telemetry': '/api/telemetry',
                    'stats': '/api/stats',
                    'health': '/health'
                }
            })
        
        @self.app.route('/video_feed')
        def video_feed():
            return Response(
                self._generate_frames(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
        
        @self.app.route('/api/coordinates')
        def api_coordinates():
            with self.lock:
                active = [p for p in self.tracked_people if p.get('active', False)]
                return jsonify({
                    'active_count': len(active),
                    'total_tracks': len(self.tracked_people),
                    'fps': round(self.fps, 1),
                    'inference_ms': round(self.inference_time_ms, 1),
                    'people': self.tracked_people,
                    'timestamp': time.time()
                })
        
        @self.app.route('/api/telemetry')
        def api_telemetry():
            return jsonify(self.telemetry.get_full_telemetry())
        
        @self.app.route('/api/telemetry/device')
        def api_telemetry_device():
            return jsonify(self.telemetry.get_metrics())
        
        @self.app.route('/api/telemetry/containers')
        def api_telemetry_containers():
            return jsonify(self.telemetry.get_containers())
        
        @self.app.route('/api/stats')
        def api_stats():
            uptime = time.time() - self.session_start
            return jsonify({
                'uptime_seconds': int(uptime),
                'total_frames': self.total_frames,
                'total_detections': self.total_detections,
                'avg_fps': round(self.total_frames / uptime, 1) if uptime > 0 else 0,
                'session_start': self.session_start
            })
        
        @self.app.route('/health')
        def health():
            return jsonify({
                'status': 'healthy' if self.running else 'stopped',
                'fps': round(self.fps, 1),
                'camera_connected': self.camera is not None
            })
    
    def _setup_socket_events(self):
        """Configure WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            print("🔌 Client connected")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print("🔌 Client disconnected")
        
        @self.socketio.on('request_telemetry')
        def handle_telemetry_request():
            self.socketio.emit('telemetry_update', self.telemetry.get_full_telemetry())
    
    def _generate_frames(self):
        """MJPEG stream generator"""
        while True:
            with self.lock:
                if self.current_frame is not None:
                    ret, buffer = cv2.imencode('.jpg', self.current_frame, 
                                               [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (
                            b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
                        )
            time.sleep(0.033)  # ~30 FPS max
    
    def _draw_annotations(self, frame: np.ndarray, tracks: list) -> np.ndarray:
        """Draw bounding boxes and labels on frame"""
        annotated = frame.copy()
        
        for track in tracks:
            if not track.get('active', False):
                continue
            
            x = int(track['x'])
            y = int(track['y'])
            w = int(track['width'])
            h = int(track['height'])
            track_id = track.get('id', 0)
            conf = track.get('confidence', 0)
            
            # Draw bounding box
            color = (0, 255, 0)  # Green for active tracks
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            
            # Draw label background
            label = f"ID:{track_id} {conf:.0%}"
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x, y - label_h - 8), (x + label_w + 4, y), color, -1)
            
            # Draw label text
            cv2.putText(annotated, label, (x + 2, y - 4),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Draw FPS overlay
        fps_label = f"FPS: {self.fps:.1f} | Inference: {self.inference_time_ms:.1f}ms"
        cv2.putText(annotated, fps_label, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Draw active count
        active_count = len([t for t in tracks if t.get('active', False)])
        count_label = f"Active: {active_count}"
        cv2.putText(annotated, count_label, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        return annotated
    
    def _processing_loop(self):
        """Main processing loop running in background thread"""
        print("🔄 Starting processing loop...")
        
        frame_count = 0
        fps_start_time = time.time()
        last_emit_time = time.time()
        last_telemetry_emit = time.time()
        
        while self.running:
            loop_start = time.time()
            
            # 1. Get frame from camera
            success, frame = self.camera.get_frame()
            if not success or frame is None:
                time.sleep(0.01)
                continue
            
            # 2. Run detection
            inference_start = time.time()
            detections = self.detector.detect(frame)
            self.inference_time_ms = (time.time() - inference_start) * 1000
            
            # 3. Update tracker
            tracks = self.tracker.update(detections, frame.shape[:2])
            
            # 4. Transform coordinates (if calibrated)
            tracks = self.geometry.transform_tracks(tracks)
            
            # 5. Draw annotations
            annotated_frame = self._draw_annotations(frame, tracks)
            
            # 6. Update shared state
            with self.lock:
                self.current_frame = annotated_frame
                self.tracked_people = tracks
            
            # 7. Update statistics
            self.total_frames += 1
            self.total_detections += len(detections)
            frame_count += 1
            
            # 8. Calculate FPS
            elapsed = time.time() - fps_start_time
            if elapsed >= 1.0:
                self.fps = frame_count / elapsed
                frame_count = 0
                fps_start_time = time.time()
                
                active_count = len([t for t in tracks if t.get('active', False)])
                print(f"📊 FPS: {self.fps:.1f} | Active: {active_count} | "
                      f"Inference: {self.inference_time_ms:.1f}ms")
            
            # 9. Emit WebSocket updates (10 Hz)
            if time.time() - last_emit_time >= 0.1:
                with self.lock:
                    self.socketio.emit('coordinate_tracking_update', {
                        'active_count': len([t for t in tracks if t.get('active', False)]),
                        'fps': round(self.fps, 1),
                        'inference_ms': round(self.inference_time_ms, 1),
                        'people': tracks,
                        'timestamp': time.time()
                    })
                last_emit_time = time.time()
            
            # 10. Emit telemetry updates (0.5 Hz)
            if time.time() - last_telemetry_emit >= 2.0:
                self.socketio.emit('telemetry_update', self.telemetry.get_full_telemetry())
                last_telemetry_emit = time.time()
    
    def start(self):
        """Start the application"""
        self.running = True
        self.session_start = time.time()
        
        # Start processing thread
        process_thread = threading.Thread(target=self._processing_loop, daemon=True)
        process_thread.start()
        
        # Start web server
        print("=" * 60)
        print("🚀 Minimart Tracker - Jetson Orin Nano Edition")
        print("=" * 60)
        print(f"📡 API:        http://0.0.0.0:5000")
        print(f"📹 Video Feed: http://0.0.0.0:5000/video_feed")
        print(f"🔌 WebSocket:  ws://0.0.0.0:5000")
        print("=" * 60)
        
        try:
            self.socketio.run(
                self.app,
                host='0.0.0.0',
                port=5000,
                debug=False,
                allow_unsafe_werkzeug=True
            )
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the application"""
        print("\n🛑 Stopping...")
        self.running = False
        self.camera.release()
        self.telemetry.stop()
        print("✅ Stopped")


def main():
    """Application entry point - Composition Root"""
    
    print("🔧 Initializing services...")
    
    # 1. Initialize Services
    camera_svc = get_camera_service()
    detection_svc = DetectionService(confidence_threshold=0.4)
    tracking_svc = TrackingService(max_distance=150, max_disappeared=30)
    geometry_svc = GeometryService(calibration_file="coordinate_calibration.json")
    
    # 2. Create Application with Injected Dependencies
    app = MinimartTrackerApp(
        camera=camera_svc,
        detector=detection_svc,
        tracker=tracking_svc,
        geometry=geometry_svc
    )
    
    # 3. Launch
    app.start()


if __name__ == "__main__":
    main()
