import cv2
import numpy as np
import os
import requests # Requires 'requests' in requirements.txt
from ultralytics import YOLO
from domain.interfaces import IDetector

# Import legacy dependency (only works if running natively)
try:
    from crowdhuman_hailo_detector import get_hailo_detector
    HAS_ENHANCED_DETECTOR = True
except ImportError:
    HAS_ENHANCED_DETECTOR = False

class RemoteHailoDetector(IDetector):
    """Client that talks to the native hailo_sidecar.py"""
    def __init__(self, url="http://127.0.0.1:6000/detect"):
        self.url = url
        print(f"📡 Initialized Remote Detector pointing to {self.url}")

    def detect(self, frame: np.ndarray) -> list:
        try:
            # 1. Encode frame to JPEG to send over HTTP
            success, encoded_img = cv2.imencode('.jpg', frame)
            if not success:
                return []
            
            # 2. POST to Sidecar
            files = {'image': encoded_img.tobytes()}
            response = requests.post(self.url, files=files, timeout=1.0)
            
            if response.status_code != 200:
                print(f"⚠️ Sidecar Error: {response.status_code}")
                return []
            
            # 3. Parse JSON Response
            # Sidecar returns: [{'bbox': [x1, y1, x2, y2], 'confidence': 0.9, ...}]
            sidecar_results = response.json()
            formatted_results = []
            
            for det in sidecar_results:
                x1, y1, x2, y2 = det['bbox']
                formatted_results.append({
                    'confidence': det['confidence'],
                    'x': float(x1),
                    'y': float(y1),
                    'width': float(x2 - x1),
                    'height': float(y2 - y1)
                })
            return formatted_results

        except Exception as e:
            # Print only first few characters of error to avoid log spam
            print(f"⚠️ Remote Inference Failed: {str(e)[:50]}...")
            return []

class DetectionService(IDetector):
    def __init__(self, confidence_threshold: float = 0.4):
        self.detector = None
        self.model = None
        self.confidence_threshold = confidence_threshold
        self.use_enhanced = False
        self._initialize_model()

    def _initialize_model(self):
        # 0. Check for Remote Sidecar Mode (New!)
        if os.environ.get('USE_REMOTE_DETECTOR', 'false').lower() == 'true':
            print("🚀 Initializing Remote Hailo Client...")
            self.detector = RemoteHailoDetector(url="http://127.0.0.1:6000/detect")
            self.use_enhanced = True
            return

        # 1. Try Local Enhanced Hailo Detector (Native only)
        if HAS_ENHANCED_DETECTOR:
            print("🚀 Initializing Local Hailo Detector...")
            self.detector = get_hailo_detector(
                "models/crowdhuman.hef",
                cv2_ref_passed=cv2,
                np_ref_passed=np
            )
            if self.detector:
                self.use_enhanced = True
                print("✅ Local Hailo Detector loaded")
                return

        # 2. Fallback to Standard YOLO
        self.use_enhanced = False
        print("⚠️  Fallback: Loading Standard YOLOv8s (CPU)")
        self.model = YOLO("yolov8s.pt")

    def detect(self, frame: np.ndarray) -> list:
        if self.use_enhanced:
            # Both Remote and Local Hailo use this path now
            return self.detector.detect(frame)
        else:
            # Standard YOLO Logic
            raw_detections = []
            results = self.model(frame, conf=self.confidence_threshold, classes=[0], verbose=False)
            for result in results:
                if result.boxes:
                    for box in result.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        raw_detections.append({
                            'confidence': float(box.conf[0]),
                            'x': float(x1),
                            'y': float(y1),
                            'width': float(x2 - x1),
                            'height': float(y2 - y1)
                        })
            return self._filter_overlapping(raw_detections)

    def _filter_overlapping(self, detections, overlap_threshold=0.5):
        # ... (Same logic as before) ...
        if len(detections) <= 1: return detections
        sorted_dets = sorted(detections, key=lambda x: (x['width'] * x['height'], x['confidence']), reverse=True)
        filtered = []
        for current in sorted_dets:
            is_dup = False
            curr_area = current['width'] * current['height']
            curr_x2 = current['x'] + current['width']
            curr_y2 = current['y'] + current['height']
            for kept in filtered:
                kept_x2 = kept['x'] + kept['width']
                kept_y2 = kept['y'] + kept['height']
                xi1 = max(current['x'], kept['x'])
                yi1 = max(current['y'], kept['y'])
                xi2 = min(curr_x2, kept_x2)
                yi2 = min(curr_y2, kept_y2)
                if xi2 > xi1 and yi2 > yi1:
                    intersection = (xi2 - xi1) * (yi2 - yi1)
                    kept_area = kept['width'] * kept['height']
                    smaller_area = min(curr_area, kept_area)
                    if (intersection / smaller_area if smaller_area > 0 else 0) > overlap_threshold and curr_area < kept_area:
                        is_dup = True
                        break
            if not is_dup: filtered.append(current)
        return filtered