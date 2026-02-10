#!/usr/bin/env python3
"""
YOLOv8s People Tracking with Real-World Coordinates
Combines persistent ID tracking with precise coordinate mapping
"""

import cv2
import numpy as np
import time
try:
    from picamera2 import Picamera2
    HAS_PICAMERA2 = True
except ImportError:
    HAS_PICAMERA2 = False
import threading
from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO
import math
from collections import defaultdict
import json
import os
import queue
from concurrent.futures import ThreadPoolExecutor

# Import our coordinate calibration system
import cv2 as cv_coord
from datetime import datetime
import threading

# Always import YOLO as fallback
from ultralytics import YOLO

# Import enhanced Hailo detector with CrowdHuman model
try:
    from crowdhuman_hailo_detector import get_hailo_detector, cleanup_hailo
    HAS_ENHANCED_DETECTOR = True
    print("✅ CrowdHuman HAILO8L detector available")
except ImportError as e:
    print(f"⚠️  Enhanced detector not available, using YOLO fallback: {e}")
    HAS_ENHANCED_DETECTOR = False

class CoordinateMapper:
    def __init__(self, calibration_file="coordinate_calibration.json"):
        self.homography_matrix = None
        self.load_calibration(calibration_file)
    
    def load_calibration(self, filename):
        """Load coordinate calibration from JSON file"""
        try:
            with open(filename, 'r') as f:
                calibration_data = json.load(f)
            
            self.homography_matrix = np.array(calibration_data['homography_matrix'])
            print(f"✅ Camera calibration loaded for coordinate tracking.")
            return True
        except Exception as e:
            print(f"❌ Could not load coordinate calibration: {e}")
            return False
    
    def pixel_to_world_coordinates(self, pixel_points):
        """Convert pixel coordinates to world coordinates"""
        if self.homography_matrix is None:
            return None
        
        try:
            # Ensure points are in correct format
            if isinstance(pixel_points, (list, tuple)) and len(pixel_points) == 2:
                pixel_points = np.array([[pixel_points]], dtype=np.float32)
            elif pixel_points.ndim == 1:
                pixel_points = pixel_points.reshape(1, 1, -1).astype(np.float32)
            else:
                pixel_points = pixel_points.reshape(-1, 1, 2).astype(np.float32)
            
            # Convert using homography
            world_points = cv_coord.perspectiveTransform(pixel_points, self.homography_matrix)
            return world_points.reshape(-1, 2)[0]  # Return first point as tuple
        except Exception as e:
            print(f"Coordinate conversion error: {e}")
            return None


class PersonTracker:
    def __init__(self, max_distance=100, max_age=30):
        self.tracks = {}
        self.next_id = 1
        self.max_distance = max_distance
        self.max_age = max_age
        
    def calculate_distance(self, box1, box2):
        center1 = ((box1[0] + box1[2]) / 2, (box1[1] + box1[3]) / 2)
        center2 = ((box2[0] + box2[2]) / 2, (box2[1] + box2[3]) / 2)
        return math.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
    
    def calculate_iou(self, box1, box2):
        x1, y1, x2, y2 = box1
        x3, y3, x4, y4 = box2
        
        xi1 = max(x1, x3)
        yi1 = max(y1, y3)
        xi2 = min(x2, x4)
        yi2 = min(y2, y4)
        
        if xi2 <= xi1 or yi2 <= yi1:
            return 0
            
        intersection = (xi2 - xi1) * (yi2 - yi1)
        area1 = (x2 - x1) * (y2 - y1)
        area2 = (x4 - x3) * (y4 - y3)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0
    
    def update(self, detections):
        # Age all existing tracks
        for track_id in list(self.tracks.keys()):
            self.tracks[track_id]['age'] += 1
            self.tracks[track_id]['active'] = False
            
        # Remove old tracks
        for track_id in list(self.tracks.keys()):
            if self.tracks[track_id]['age'] > self.max_age:
                del self.tracks[track_id]
        
        if not detections:
            return []
            
        # Convert detections to format [x1, y1, x2, y2, confidence]
        detection_boxes = []
        for det in detections:
            detection_boxes.append([det['x'], det['y'], 
                                  det['x'] + det['width'], 
                                  det['y'] + det['height'], 
                                  det['confidence']])
        
        # Association logic (same as before)
        track_ids = list(self.tracks.keys())
        if track_ids and detection_boxes:
            cost_matrix = np.zeros((len(track_ids), len(detection_boxes)))
            
            for i, track_id in enumerate(track_ids):
                track_box = self.tracks[track_id]['box']
                for j, det_box in enumerate(detection_boxes):
                    distance = self.calculate_distance(track_box[:4], det_box[:4])
                    iou = self.calculate_iou(track_box[:4], det_box[:4])
                    cost = distance * (1 - iou * 0.7)
                    cost_matrix[i, j] = cost
            
            # Simple greedy assignment
            assigned_tracks = set()
            assigned_detections = set()
            assignments = []
            
            for _ in range(min(len(track_ids), len(detection_boxes))):
                min_cost = float('inf')
                best_track = -1
                best_det = -1
                
                for i in range(len(track_ids)):
                    if i in assigned_tracks:
                        continue
                    for j in range(len(detection_boxes)):
                        if j in assigned_detections:
                            continue
                        if cost_matrix[i, j] < min_cost and cost_matrix[i, j] < self.max_distance:
                            min_cost = cost_matrix[i, j]
                            best_track = i
                            best_det = j
                
                if best_track != -1 and best_det != -1:
                    assignments.append((best_track, best_det))
                    assigned_tracks.add(best_track)
                    assigned_detections.add(best_det)
            
            # Update assigned tracks
            for track_idx, det_idx in assignments:
                track_id = track_ids[track_idx]
                detection = detection_boxes[det_idx]
                
                self.tracks[track_id]['box'] = detection
                self.tracks[track_id]['age'] = 0
                self.tracks[track_id]['active'] = True
                self.tracks[track_id]['last_seen'] = time.time()
        else:
            assigned_detections = set()
        
        # Create new tracks for unassigned detections
        for i, detection in enumerate(detection_boxes):
            if i not in assigned_detections:
                track_id = self.next_id
                self.next_id += 1
                
                self.tracks[track_id] = {
                    'box': detection,
                    'age': 0,
                    'active': True,
                    'created': time.time(),
                    'last_seen': time.time(),
                    'color': self.generate_color(track_id)
                }
        
        # Return active tracks with their IDs
        result = []
        for track_id, track in self.tracks.items():
            if track['active'] or track['age'] <= 5:
                box = track['box']
                result.append({
                    'id': track_id,
                    'x': box[0],
                    'y': box[1],
                    'width': box[2] - box[0],
                    'height': box[3] - box[1],
                    'confidence': box[4],
                    'active': track['active'],
                    'age': track['age'],
                    'color': track['color']
                })
        
        return result
    
    def generate_color(self, track_id):
        np.random.seed(track_id * 42)
        return tuple(map(int, np.random.randint(50, 255, 3)))

class YOLOv8sTrackingWithCoordinates:
    def __init__(self):
        # Initialize enhanced detector or fallback
        global HAS_ENHANCED_DETECTOR
        if HAS_ENHANCED_DETECTOR:
            print("🚀 Initializing CrowdHuman YOLO v8 HAILO8L detector...")
            self.detector = get_hailo_detector(
                "yolo_v8_crowdhuman--640x640_quant_hailort_multidevice_1",
                cv2_ref_passed=cv2,
                np_ref_passed=np
            )
            if self.detector:
                print("✅ CrowdHuman YOLO v8 HAILO8L detector loaded successfully")
                print(f"   - Model: YOLO v8 CrowdHuman (person-focused)")
                print(f"   - Device: HAILO8L hardware acceleration")
                print(f"   - Classes: 1 (person)")
            else:
                print("❌ CrowdHuman detector failed, falling back to YOLO")
                HAS_ENHANCED_DETECTOR = False
        
        if not HAS_ENHANCED_DETECTOR:
            # Fallback to custom trained YOLO model
            self.model_path = "models/custom_yolo_deployment/custom_yolo.pt"
            print(f"🔄 Loading custom trained YOLOv8s model: {self.model_path}")
            if os.path.exists(self.model_path):
                self.model = YOLO(self.model_path)
                print("✅ Custom trained YOLOv8s model loaded successfully")
            else:
                print("❌ Custom model not found, using default YOLOv8s")
                self.model = YOLO("yolov8s.pt")
                print("✅ Default YOLOv8s model loaded successfully")
            self.detector = None
        
        # Initialize coordinate mapper
        print("🌍 Initializing coordinate system...")
        self.coordinate_mapper = CoordinateMapper("coordinate_calibration.json")
        print("✅ Coordinate system ready")
        
        
        # Initialize camera
        print("🔄 Initializing camera...")
        self.camera = None
        self.use_picamera2 = False
        
        # First try Picamera2 (preferred for Raspberry Pi)
        if HAS_PICAMERA2:
            try:
                print("   Trying Picamera2...")
                self.camera = Picamera2()
                
                # Configure dual stream like the example
                normalSize = (1920, 1080)
                lowresSize = (1280, 720)
                
                config = self.camera.create_preview_configuration(
                    main={"size": normalSize, "format": "RGB888"},
                    lores={"size": lowresSize, "format": "RGB888"}
                )
                self.camera.configure(config)
                self.camera.start()
                
                # Test capture
                test_frame = self.camera.capture_array("lores")
                if test_frame is not None and test_frame.size > 0:
                    self.use_picamera2 = True
                    print("✅ Picamera2 initialized successfully with dual stream")
                    print(f"   Main stream: {normalSize}, Detection stream: {lowresSize}")
                else:
                    raise Exception("Test capture failed")
                    
            except Exception as e:
                print(f"   Picamera2 failed: {e}")
                try:
                    if self.camera:
                        self.camera.stop()
                except:
                    pass
                self.camera = None
        
        # Fallback to OpenCV if Picamera2 failed
        if self.camera is None:
            print("   Trying OpenCV VideoCapture...")
            camera_indices = [0, 1, 2, 3, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
            
            for i in camera_indices:
                try:
                    print(f"   Trying /dev/video{i}...")
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            self.camera = cap
                            self.use_picamera2 = False
                            print(f"✅ OpenCV camera initialized on /dev/video{i}")
                            # Set camera properties for OpenCV
                            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            self.camera.set(cv2.CAP_PROP_FPS, 30)
                            break
                    cap.release()
                except Exception as e:
                    print(f"   /dev/video{i} failed: {e}")
                    continue
        
        if self.camera is None:
            raise Exception("No working camera found - tried Picamera2 and OpenCV backends")
        
        print("✅ Camera initialized successfully")
        
        # Initialize tracker
        self.tracker = PersonTracker(max_distance=150, max_age=30)
        print("✅ Person tracker initialized")
        
        # Detection settings
        self.confidence_threshold = 0.4
        self.running = False
        
        # Enhanced features
        self.use_enhanced_detector = HAS_ENHANCED_DETECTOR and self.detector is not None
        self.frame_id_counter = 0
        
        # Performance tracking
        self.detection_times = []
        self.last_fps_update = time.time()
        self.current_frame = None
        self.tracked_people = []
        self.fps = 0
        self.last_socketio_emit = time.time()
        
        # Flask app setup
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'yolov8s_coordinates'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        self.setup_routes()
        
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return """
<!DOCTYPE html>
<html>
<head>
    <title>YOLOv8s People Tracking with Real-World Coordinates</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; padding: 20px; background: white; border-radius: 10px; margin-bottom: 20px; }
        .video-container { background: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
        .stats { background: white; padding: 20px; border-radius: 10px; }
        .person-box { background: #e8f5e8; padding: 15px; margin: 5px; border-radius: 5px; display: inline-block; min-width: 250px; vertical-align: top; }
        .person-inactive { background: #ffe8e8; }
        #videoFeed { max-width: 100%; height: auto; border: 2px solid #ddd; border-radius: 10px; }
        .metrics { display: flex; justify-content: space-around; margin-top: 20px; }
        .metric { text-align: center; }
        .people-grid { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
        .id-badge { font-weight: bold; font-size: 1.2em; padding: 5px 10px; border-radius: 20px; color: white; display: inline-block; margin-right: 10px; }
        .coord-display { background: #f0f8ff; padding: 8px; border-radius: 5px; margin-top: 5px; font-family: monospace; }
        .real-world-coords { color: #0066cc; font-weight: bold; }
        .pixel-coords { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 YOLOv8s People Tracking with Real-World Coordinates</h1>
            <p>Real-time detection with persistent IDs and accurate coordinate mapping</p>
        </div>
        
        <div class="video-container" style="background: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
            <h3>📹 Live Video Feed</h3>
            <img id="videoFeed" src="/video_feed" alt="Live Video Feed with Coordinate Tracking" style="max-width: 100%; height: auto; border: 2px solid #ddd; border-radius: 10px;">
        </div>
        
        
        <div class="stats">
            <h3>Tracking & Coordinate Statistics</h3>
            <div class="metrics">
                <div class="metric">
                    <h4 id="peopleCount">0</h4>
                    <p>Active People</p>
                </div>
                <div class="metric">
                    <h4 id="totalTracks">0</h4>
                    <p>Total Tracks</p>
                </div>
                <div class="metric">
                    <h4 id="fps">0</h4>
                    <p>FPS</p>
                </div>
                <div class="metric">
                    <h4 id="avgConfidence">0%</h4>
                    <p>Avg Confidence</p>
                </div>
            </div>
            
            <h3>People with Real-World Coordinates</h3>
            <div id="peopleGrid" class="people-grid"></div>
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        const socket = io();
        
        socket.on('coordinate_tracking_update', function(data) {
            document.getElementById('peopleCount').textContent = data.active_count;
            document.getElementById('totalTracks').textContent = data.total_tracks;
            document.getElementById('fps').textContent = data.fps.toFixed(1);
            document.getElementById('avgConfidence').textContent = (data.avg_confidence * 100).toFixed(1) + '%';
            
            const peopleGrid = document.getElementById('peopleGrid');
            peopleGrid.innerHTML = '';
            
            data.people.forEach((person) => {
                const personDiv = document.createElement('div');
                personDiv.className = 'person-box' + (person.active ? '' : ' person-inactive');
                
                const color = `rgb(${person.color[0]}, ${person.color[1]}, ${person.color[2]})`;
                
                personDiv.innerHTML = `
                    <span class="id-badge" style="background-color: ${color}">ID ${person.id}</span>
                    <br>
                    <strong>Status:</strong> ${person.active ? 'Active' : 'Lost (' + person.age + ' frames)'}<br>
                    <strong>Confidence:</strong> ${(person.confidence * 100).toFixed(1)}%<br>
                    
                    <div class="coord-display">
                        <div class="pixel-coords">📱 Pixel Center: (${person.center_pixel_x.toFixed(0)}, ${person.center_pixel_y.toFixed(0)})</div>
                        <div class="bbox-coords">📦 BBox: x=${person.x.toFixed(0)}, y=${person.y.toFixed(0)}, w=${person.width.toFixed(0)}, h=${person.height.toFixed(0)}</div>
                        <div class="real-world-coords">🌍 Mapped: (${person.real_world_x.toFixed(1)}, ${person.real_world_y.toFixed(1)})</div>
                    </div>
                    
                    <small>Bbox: ${person.width.toFixed(0)}×${person.height.toFixed(0)}</small>
                `;
                peopleGrid.appendChild(personDiv);
            });
            
        });
    </script>
</body>
</html>
            """
        
        @self.app.route('/video_feed')
        def video_feed():
            return Response(self.generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/api/coordinates')
        def api_coordinates():
            active_people = [p for p in self.tracked_people if p['active']]
            return jsonify({
                'active_count': len(active_people),
                'total_tracks': len(self.tracked_people),
                'fps': self.fps,
                'avg_confidence': np.mean([p['confidence'] for p in active_people]) if active_people else 0,
                'people': self.tracked_people
            })
    
    def detect_and_track_with_coordinates(self, frame):
        """Run enhanced YOLOv8s detection, tracking, and coordinate mapping"""
        start_time = time.time()
        
        if self.use_enhanced_detector:
            # Use enhanced Hailo detector with dynamic resolution and parallel processing
            self.frame_id_counter += 1
            enhanced_detections = self.detector.detect(frame)
            
            # Convert enhanced detections to standard format
            detections = []
            for det in enhanced_detections:
                x1, y1, x2, y2 = det.bbox
                detections.append({
                    'confidence': det.confidence,
                    'x': float(x1),
                    'y': float(y1),
                    'width': float(x2 - x1),
                    'height': float(y2 - y1)
                })
            
            # Filter out smaller overlapping detections (face/body duplicates)
            detections = self.filter_overlapping_detections(detections)
        else:
            # Fallback to standard YOLO detection
            results = self.model(frame, conf=self.confidence_threshold, classes=[0])
            
            # Extract detections
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = float(box.conf[0])
                        
                        detections.append({
                            'confidence': confidence,
                            'x': float(x1),
                            'y': float(y1),
                            'width': float(x2 - x1),
                            'height': float(y2 - y1)
                        })
            
            # Filter out smaller overlapping detections (face/body duplicates)
            detections = self.filter_overlapping_detections(detections)
        
        # Track performance
        detection_time = time.time() - start_time
        self.detection_times.append(detection_time)
        if len(self.detection_times) > 30:  # Keep only recent times
            self.detection_times.pop(0)
        
        # Update tracker with detections
        tracked_people = self.tracker.update(detections)
        
        # Add real-world coordinates for each tracked person
        for person in tracked_people:
            # Get center position of bounding box
            bbox = [person['x'], person['y'], person['width'], person['height']]
            
            # Calculate center of bounding box
            center_x = person['x'] + person['width'] / 2
            center_y = person['y'] + person['height'] / 2
            center_pixel = (center_x, center_y)
            
            # Use center position for coordinate mapping
            real_world_pos = self.coordinate_mapper.pixel_to_world_coordinates(center_pixel)
            
            # Debug output
            if real_world_pos is not None:
                print(f"Debug: Pixel({center_x:.0f}, {center_y:.0f}) -> World({real_world_pos[0]:.1f}, {real_world_pos[1]:.1f})")
            
            # Add coordinate information (convert to Python floats for JSON serialization)
            person['center_pixel_x'] = float(center_x)
            person['center_pixel_y'] = float(center_y)
            person['real_world_x'] = float(real_world_pos[0]) if real_world_pos is not None else 0.0
            person['real_world_y'] = float(real_world_pos[1]) if real_world_pos is not None else 0.0
        
        # Draw tracking results with coordinates on frame
        annotated_frame = frame.copy()
        
        for person in tracked_people:
            x1 = int(person['x'])
            y1 = int(person['y'])
            x2 = int(person['x'] + person['width'])
            y2 = int(person['y'] + person['height'])
            
            color = person['color']
            thickness = 3 if person['active'] else 2
            
            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)
            
            # Draw ID and status
            status = "ACTIVE" if person['active'] else f"LOST ({person['age']})"
            id_label = f"ID {person['id']} - {status}"
            
            # Draw real-world coordinates
            coord_label = f"({person['real_world_x']:.1f}, {person['real_world_y']:.1f})"
            
            # Background for labels
            label_size = cv2.getTextSize(id_label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            coord_size = cv2.getTextSize(coord_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            
            cv2.rectangle(annotated_frame, (x1, y1-label_size[1]-coord_size[1]-15), 
                         (x1+max(label_size[0], coord_size[0]), y1), color, -1)
            
            # ID label
            cv2.putText(annotated_frame, id_label, (x1, y1-coord_size[1]-8), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Coordinate label
            cv2.putText(annotated_frame, coord_label, (x1, y1-3), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            
            # Draw center position marker
            center_x, center_y = int(person['center_pixel_x']), int(person['center_pixel_y'])
            cv2.circle(annotated_frame, (center_x, center_y), 5, color, -1)
            cv2.circle(annotated_frame, (center_x, center_y), 8, (255, 255, 255), 2)
        
        # Add enhanced detector information if available
        if self.use_enhanced_detector and self.detector:
            # Performance metrics
            avg_detection_time = np.mean(self.detection_times) if self.detection_times else 0
            current_fps = 1.0 / avg_detection_time if avg_detection_time > 0 else 0
            
            # Enhanced detector info
            if hasattr(self.detector, 'dynamic_resolution') and self.detector.dynamic_resolution:
                info_text = f"Enhanced Hailo | Resolution: {self.detector.current_resolution} | FPS: {current_fps:.1f}"
                mode_text = "Mode: Parallel" if (self.detector.parallel_processing and self.detector.parallel_active) else "Mode: Serial"
            else:
                info_text = f"Enhanced Hailo | FPS: {current_fps:.1f}"
                mode_text = "Mode: Standard"
            
            # Draw enhanced info overlay
            cv2.putText(annotated_frame, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(annotated_frame, mode_text, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Note: AWS coordinate data will be sent via detection_loop SocketIO emit to avoid hanging issues
        
        return annotated_frame, tracked_people
    
    def filter_overlapping_detections(self, detections, overlap_threshold=0.5):
        """Filter out smaller overlapping detections to prevent face/body duplicates"""
        if len(detections) <= 1:
            return detections
        
        # Sort by area (largest first) and then by confidence
        sorted_detections = sorted(detections, 
                                 key=lambda x: (x['width'] * x['height'], x['confidence']), 
                                 reverse=True)
        
        filtered_detections = []
        
        for current_det in sorted_detections:
            is_duplicate = False
            current_x1 = current_det['x']
            current_y1 = current_det['y']
            current_x2 = current_det['x'] + current_det['width']
            current_y2 = current_det['y'] + current_det['height']
            current_area = current_det['width'] * current_det['height']
            
            for kept_det in filtered_detections:
                kept_x1 = kept_det['x']
                kept_y1 = kept_det['y']
                kept_x2 = kept_det['x'] + kept_det['width']
                kept_y2 = kept_det['y'] + kept_det['height']
                kept_area = kept_det['width'] * kept_det['height']
                
                # Calculate intersection area
                xi1 = max(current_x1, kept_x1)
                yi1 = max(current_y1, kept_y1)
                xi2 = min(current_x2, kept_x2)
                yi2 = min(current_y2, kept_y2)
                
                if xi2 > xi1 and yi2 > yi1:
                    intersection_area = (xi2 - xi1) * (yi2 - yi1)
                    
                    # Calculate overlap ratio with respect to smaller box
                    smaller_area = min(current_area, kept_area)
                    overlap_ratio = intersection_area / smaller_area if smaller_area > 0 else 0
                    
                    # If significant overlap and current is smaller, mark as duplicate
                    if overlap_ratio > overlap_threshold and current_area < kept_area:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                filtered_detections.append(current_det)
        
        return filtered_detections
    
    def generate_frames(self):
        """Generate video frames for web streaming"""
        while True:
            if self.current_frame is not None:
                ret, buffer = cv2.imencode('.jpg', self.current_frame)
                if ret:
                    frame = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.033)  # ~30 FPS
    
    def detection_loop(self):
        """Main detection, tracking, and coordinate mapping loop"""
        print("🔄 Starting detection, tracking, and coordinate mapping...")
        frame_count = 0
        start_time = time.time()
        
        while self.running:
            try:
                # Capture frame based on camera type
                if self.use_picamera2:
                    # Use Picamera2 low-resolution stream for detection
                    frame = self.camera.capture_array("lores")
                    # Frame is already in RGB format from Picamera2
                else:
                    # Use OpenCV
                    ret, frame = self.camera.read()
                    if not ret:
                        continue
                    # Convert BGR to RGB for YOLO
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Run detection, tracking, and coordinate mapping
                annotated_frame, tracked_people = self.detect_and_track_with_coordinates(frame)
                
                # Update current frame and results
                self.current_frame = annotated_frame
                self.tracked_people = tracked_people
                
                # Emit SocketIO update every 2 seconds regardless of FPS calculation
                current_time = time.time()
                if (current_time - self.last_socketio_emit) >= 2.0:
                    active_people = [p for p in tracked_people if p['active']]
                    print(f"📊 SocketIO Emit: {len(active_people)} active, {len(tracked_people)} total")
                    
                    # Emit coordinate tracking update
                    self.socketio.emit('coordinate_tracking_update', {
                        'active_count': len(active_people),
                        'total_tracks': len(tracked_people),
                        'fps': self.fps,
                        'avg_confidence': np.mean([p['confidence'] for p in active_people]) if active_people else 0,
                        'people': tracked_people
                    })
                    self.last_socketio_emit = current_time
                
                # Calculate FPS
                frame_count += 1
                elapsed = time.time() - start_time
                if elapsed > 1.0:
                    print(f"🔄 FPS update: {frame_count}/{elapsed:.1f}s = {frame_count/elapsed:.1f} FPS")
                    self.fps = frame_count / elapsed
                    frame_count = 0
                    start_time = time.time()
                    
                    # Count active people
                    active_people = [p for p in tracked_people if p['active']]
                    print(f"📊 Emitting update: {len(active_people)} active, {len(tracked_people)} total")
                    
                    # Emit coordinate tracking update
                    self.socketio.emit('coordinate_tracking_update', {
                        'active_count': len(active_people),
                        'total_tracks': len(tracked_people),
                        'fps': self.fps,
                        'avg_confidence': np.mean([p['confidence'] for p in active_people]) if active_people else 0,
                        'people': tracked_people
                    })
                    
                    # Print coordinate information
                    coords_info = []
                    for person in active_people:
                        coords_info.append(f"ID{person['id']}:({person['real_world_x']:.1f},{person['real_world_y']:.1f})")
                    
                    print(f"🎯 Active: {len(active_people)} | FPS: {self.fps:.1f} | Coords: {' '.join(coords_info)}")
                
            except Exception as e:
                print(f"❌ Detection error: {e}")
                time.sleep(0.1)
    
    def start(self):
        """Start the enhanced detection, tracking, and coordinate system"""
        if self.use_enhanced_detector:
            print("🚀 Starting Enhanced Hailo YOLOv8s People Tracking with Real-World Coordinates")
        else:
            print("🚀 Starting Standard YOLOv8s People Tracking with Real-World Coordinates")
        print("=" * 80)
        
        self.running = True
        
        # Start detection thread
        detection_thread = threading.Thread(target=self.detection_loop)
        detection_thread.daemon = True
        detection_thread.start()
        
        print("✅ Complete tracking system started")
        print("🌐 Web interface: http://localhost:5000")
        print("📱 API endpoint: http://localhost:5000/api/coordinates")
        if self.use_enhanced_detector:
            features = [
                "Enhanced Hailo Detection",
                "Persistent IDs", 
                "Real-world coordinates"
            ]
            if hasattr(self.detector, 'dynamic_resolution') and self.detector.dynamic_resolution:
                features.append("Dynamic Resolution")
            if hasattr(self.detector, 'parallel_processing') and self.detector.parallel_processing:
                features.append("Parallel Processing")
            print(f"🏷️ Enhanced Features: {' + '.join(features)}")
        else:
            print("🏷️ Features: Persistent IDs + Real-world coordinates")
        print("⚡ Press Ctrl+C to stop")
        
        # Start Flask app
        try:
            self.socketio.run(self.app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
        except KeyboardInterrupt:
            print("\n🛑 Stopping enhanced tracking system...")
            self.running = False
            if self.use_picamera2:
                self.camera.stop()
            else:
                self.camera.release()
            
            # Cleanup enhanced detector if used
            if self.use_enhanced_detector and HAS_ENHANCED_DETECTOR:
                try:
                    cleanup_hailo()
                    print("✅ Enhanced detector cleaned up")
                except:
                    pass
            
            print("✅ Enhanced tracking system stopped")

def main():
    """Main function"""
    try:
        detector = YOLOv8sTrackingWithCoordinates()
        detector.start()
    except Exception as e:
        print(f"❌ Failed to start complete tracking system: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    main()