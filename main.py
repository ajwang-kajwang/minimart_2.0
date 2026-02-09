#!/usr/bin/env python3
"""
Minimart Pi 5 Production - API Server
Role: Provides Video Stream & Real-time Data to React Frontend
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
        # 1. Initialize Hardware
        print("🔌 Initializing Pi 5 Hardware...")
        self.camera = CameraService()
        self.detector = DetectionService(confidence_threshold=0.5) 
        
        # 2. Initialize Logic
        self.tracker = TrackingService(max_distance=150, max_age=30)
        self.analytics = AnalyticsService()
        
        # State
        self.running = False
        self.current_frame = None
        self.fps = 0.0
        self.lock = threading.Lock()
        
        # 3. Initialize API Server
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'minimart_pi_prod'
        
        # ENABLE CORS: Allow React (on any port) to access this API
        CORS(self.app, resources={r"/*": {"origins": "*"}})
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='gevent')
        
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return jsonify({
                'status': 'Online', 
                'service': 'Minimart Orchestrator',
                'endpoints': ['/video_feed', '/api/status']
            })

        @self.app.route('/video_feed')
        def video_feed():
            return Response(self._generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/api/status')
        def api_status():
            return jsonify({'fps': self.fps, 'active_tracks': len(self.analytics.people_stats)})

    def _generate_frames(self):
        while True:
            time.sleep(0.04) # Cap streaming at ~25 FPS
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
        last_emit = time.time()
        
        while self.running:
            success, frame = self.camera.get_frame()
            if not success:
                time.sleep(0.01)
                continue
            
            # 1. Inference & Tracking
            detections = self.detector.detect(frame)
            tracks = self.tracker.update(detections)
            self.analytics.update(tracks)
            
            # 2. Update Current Frame (Raw, no drawing needed as React draws boxes)
            # We send raw frames to keep the stream clean, or we can draw debug info.
            # For this dashboard, let's keep it clean since React draws the overlay.
            with self.lock:
                self.current_frame = frame.copy()
            
            # 3. Stats Calculation
            frame_count += 1
            if time.time() - start_time > 1.0:
                self.fps = frame_count / (time.time() - start_time)
                print(f"📊 FPS: {self.fps:.1f} | Active: {len(tracks)}")
                frame_count, start_time = 0, time.time()
                
            # 4. Socket Broadcast (The Fix)
            if time.time() - last_emit > 0.1: # 10Hz updates
                active_count = len([t for t in tracks if t.get('active')])
                
                # CRITICAL: This structure matches VisionFeed.tsx exactly
                self.socketio.emit('coordinate_tracking_update', {
                    'fps': self.fps,               # Fixes the .toFixed crash
                    'active_count': active_count,  # Fixes the object count
                    'people': tracks,              # Used for bounding boxes
                    'analytics_summary': self.analytics.get_llm_context()
                })
                last_emit = time.time()

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