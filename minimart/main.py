#!/usr/bin/env python3
"""
Minimart Pi 5 Production - API Server
Role: Provides Video Stream & Real-time Data to Next.js Frontend
"""

import cv2
import time
import threading
import numpy as np
import os
from flask import Flask, Response, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

# --- HARDWARE IMPORTS ---
from infrastructure.camera import CameraService
from services.detection import DetectionService 

# --- LOGIC IMPORTS ---
from services.tracking import TrackingService
from services.analytics import AnalyticsService

class MinimartPiApp:
    def __init__(self):
        print("🔌 Initializing Pi 5 Hardware...")
        self.camera = CameraService()
        self.detector = DetectionService(confidence_threshold=0.5) 
        
        self.tracker = TrackingService(max_distance=150, max_age=30)
        self.analytics = AnalyticsService()
        
        self.running = False
        self.current_frame = None
        self.fps = 0.0
        self.lock = threading.Lock()
        
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'minimart_pi_prod'
        
        # Enable CORS for the Next.js frontend
        CORS(self.app, resources={r"/*": {"origins": "*"}})
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='gevent')
        
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return jsonify({'status': 'Online', 'service': 'Minimart API', 'version': '2.0'})

        @self.app.route('/video_feed')
        def video_feed():
            return Response(self._generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/api/status')
        def api_status():
            return jsonify({
                'fps': self.fps, 
                'active_tracks': len([t for t in self.tracker.tracks if t.get('active', False)]),
                'system': 'Raspberry Pi 5'
            })

    def _generate_frames(self):
        while True:
            time.sleep(0.04)
            with self.lock:
                if self.current_frame is not None:
                    try:
                        ret, buffer = cv2.imencode('.jpg', self.current_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                        if ret:
                            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    except Exception:
                        pass

    def _processing_loop(self):
        print("🔄 Pi 5 Processing Loop Started...")
        frame_count = 0
        start_time = time.time()
        
        while self.running:
            success, frame = self.camera.get_frame()
            if not success:
                time.sleep(0.01)
                continue
            
            detections = self.detector.detect(frame)
            tracks = self.tracker.update(detections)
            self.analytics.update(tracks)
            
            # Simple visualization for the stream
            for track in tracks:
                if track.get('active'):
                    x, y, w, h = int(track['x']), int(track['y']), int(track['width']), int(track['height'])
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            with self.lock:
                self.current_frame = frame.copy()
            
            frame_count += 1
            if time.time() - start_time > 1.0:
                self.fps = frame_count / (time.time() - start_time)
                print(f"📊 FPS: {self.fps:.1f} | Active: {len(tracks)}")
                frame_count, start_time = 0, time.time()

    def start(self):
        self.running = True
        threading.Thread(target=self._processing_loop, daemon=True).start()
        print("🚀 MINIMART API READY: http://0.0.0.0:5000")
        try:
            self.socketio.run(self.app, host='0.0.0.0', port=5000, debug=False)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.running = False
        self.camera.release()
        print("🛑 System Stopped")

if __name__ == "__main__":
    app = MinimartPiApp()
    app.start()