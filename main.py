#!/usr/bin/env python3
"""
Minimart Tracking System v2.1
- Integrated Edge AI (YOLO + Tracking)
- AWS Bedrock LLM Integration (Claude 3)
- Robust Gevent Server (Video + WebSockets)
- Clean UX (Hidden Zones)
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
from infrastructure.camera import get_camera_service
from services.detection import DetectionService
from services.tracking import TrackingService
from services.telemetry import get_telemetry_service
from services.analytics import AnalyticsService

class MinimartTrackerApp:
    """Main application orchestrating all services"""
    
    def __init__(
        self,
        camera: ICameraSource,
        detector: IDetector,
        tracker: ITracker,
    ):
        # Dependencies
        self.camera = camera
        self.detector = detector
        self.tracker = tracker
        self.telemetry = get_telemetry_service()
        
        # Initialize Analytics (Loads 'config/zones.json' silently)
        self.analytics = AnalyticsService()
        
        # State
        self.running = False
        self.current_frame = None
        self.tracked_people = []
        self.fps = 0
        self.inference_time_ms = 0
        self.lock = threading.Lock()
        
        # Session stats
        self.session_start = time.time()
        self.total_frames = 0
        
        # Web Server Setup
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'minimart_jetson_v2'
        CORS(self.app)
        
        # Gevent is required for stable simultaneous Video + WebSocket streaming
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='gevent')
        
        self._setup_routes()
        self._setup_socket_events()
    
    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return jsonify({'status': 'Running', 'service': 'Minimart AI Digital Twin'})
        
        @self.app.route('/video_feed')
        def video_feed():
            return Response(self._generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/api/coordinates')
        def api_coordinates():
            with self.lock:
                return jsonify({
                    'active_count': len([p for p in self.tracked_people if p.get('active', False)]),
                    'people': self.tracked_people,
                    'store_status': self.analytics.get_llm_context()
                })
        
        @self.app.route('/api/telemetry')
        def api_telemetry():
            return jsonify(self.telemetry.get_full_telemetry())

    def _setup_socket_events(self):
        @self.socketio.on('connect')
        def handle_connect():
            print("🔌 Client connected")
            
        @self.socketio.on('ask_bedrock')
        def handle_bedrock_request(data):
            user_query = data.get('query', '')
            print(f"🤖 AI Request: {user_query}")
            
            # 1. Get Context (Backend knows where people are, even if video is clean)
            context = self.analytics.get_llm_context()
            
            # 2. Lazy Load Bedrock
            if not hasattr(self, 'bedrock'):
                try:
                    from services.bedrock_service import BedrockService
                    self.bedrock = BedrockService()
                except Exception as e:
                    print(f"❌ Bedrock Init Error: {e}")
                    self.socketio.emit('bedrock_response', {'text': "AI Service Unavailable (Check AWS Keys)"})
                    return

            # 3. Generate & Emit
            try:
                insight = self.bedrock.generate_insight(context, user_query)
                self.socketio.emit('bedrock_response', {'text': insight})
            except Exception as e:
                print(f"❌ Inference Error: {e}")
                self.socketio.emit('bedrock_response', {'text': "Error processing AI request."})

    def _generate_frames(self):
        """Robust stream generator with startup placeholder"""
        try:
            # Immediate response to prevent browser timeout
            blank = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(blank, "System Initializing...", (400, 360), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            success, buffer = cv2.imencode('.jpg', blank, [cv2.IMWRITE_JPEG_QUALITY, 50])
            if success:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception:
            pass 

        while True:
            # Yield control to Gevent event loop
            time.sleep(0.04) 
            
            with self.lock:
                if self.current_frame is not None:
                    # JPEG Quality 70 = Good balance of speed/quality
                    ret, buffer = cv2.imencode('.jpg', self.current_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    def _draw_visuals(self, frame, tracks):
        annotated = frame.copy()
        
        # Note: We intentionally do NOT draw the Zones (Green Polygons)
        # to keep the UX looking like a clean Security Feed.
        
        height, width = annotated.shape[:2]

        # Draw Detected People
        for track in tracks:
            if not track.get('active', False): continue
            
            x, y, w, h = int(track['x']), int(track['y']), int(track['width']), int(track['height'])
            
            # --- Visual Polish: Add Padding ---
            # Expands the box slightly so it doesn't look too tight/cramped
            pad_x, pad_y = 10, 15
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(width, x + w + pad_x)
            y2 = min(height, y + h + pad_y)
            
            # Draw Clean Box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Simple Label
            label = f"Customer {track['id']}"
            cv2.putText(annotated, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Status Overlay
        cv2.putText(annotated, f"Minimart AI Active | FPS: {self.fps:.1f}", (20, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        return annotated

    def _processing_loop(self):
        print("🔄 Processing loop started...")
        frame_count = 0
        fps_start = time.time()
        last_emit = time.time()
        
        while self.running:
            success, frame = self.camera.get_frame()
            if not success or frame is None:
                time.sleep(0.01)
                continue
            
            # 1. AI Pipeline
            t0 = time.time()
            detections = self.detector.detect(frame)
            self.inference_time_ms = (time.time() - t0) * 1000
            
            tracks = self.tracker.update(detections, frame.shape[:2])
            
            # 2. Update Analytics (Invisible logic)
            self.analytics.update(tracks)
            
            # 3. Visualization
            final_frame = self._draw_visuals(frame, tracks)
            
            with self.lock:
                self.current_frame = final_frame
                self.tracked_people = tracks
            
            # 4. Stats
            frame_count += 1
            if time.time() - fps_start >= 1.0:
                self.fps = frame_count / (time.time() - fps_start)
                frame_count, fps_start = 0, time.time()
                print(f"📊 FPS: {self.fps:.1f} | Active Tracks: {len(tracks)}")
            
            # 5. Dashboard Broadcast (10Hz)
            if time.time() - last_emit >= 0.1:
                self.socketio.emit('coordinate_tracking_update', {
                    'people': tracks, 
                    'analytics_summary': self.analytics.get_llm_context()
                })
                last_emit = time.time()

    def start(self):
        self.running = True
        threading.Thread(target=self._processing_loop, daemon=True).start()
        print("\n" + "="*50)
        print("🚀 MINIMART 2.1 DIGITAL TWIN READY")
        print("📹 Dashboard: http://0.0.0.0:5000")
        print("="*50 + "\n")
        
        try:
            self.socketio.run(self.app, host='0.0.0.0', port=5000, debug=False)
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        self.running = False
        self.camera.release()
        self.telemetry.stop()
        print("🛑 System Stopped")

def main():
    print("🔧 Initializing Services...")
    app = MinimartTrackerApp(
        get_camera_service(),
        DetectionService(0.4),
        TrackingService(150, 30)
    )
    app.start()

if __name__ == "__main__":
    main()