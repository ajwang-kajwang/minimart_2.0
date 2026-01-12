import cv2
import numpy as np
import os
from domain.interfaces import IDetector

# Try to import YOLO - will fall back to mock if not available
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    print("⚠️ Ultralytics not installed - using mock detector")

class DetectionService(IDetector):
    def __init__(self, confidence_threshold: float = 0.4):
        self.model = None
        self.confidence_threshold = confidence_threshold
        self._initialize_model()

    def _initialize_model(self):
        if not HAS_YOLO:
            print("🔧 Running in mock detection mode")
            return
            
        # Try to load custom model, fall back to default
        model_path = "models/custom_yolo_deployment/custom_yolo.pt"
        if os.path.exists(model_path):
            self.model = YOLO(model_path)
            print("✅ Custom trained YOLOv8s model loaded")
        else:
            try:
                self.model = YOLO("yolov8s.pt")
                print("✅ Default YOLOv8s model loaded")
            except Exception as e:
                print(f"⚠️ Could not load YOLO model: {e}")
                self.model = None

    def detect(self, frame: np.ndarray) -> list:
        raw_detections = []
        
        if self.model is None:
            # Mock detector for testing without model
            return self._mock_detect(frame)
        
        # Standard YOLO Logic
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
    
    def _mock_detect(self, frame: np.ndarray) -> list:
        """Generate mock detections for testing without a model"""
        # For testing, return empty or random detections
        return []

    def _filter_overlapping(self, detections, overlap_threshold=0.5):
        """Logic extracted from original filter_overlapping_detections method"""
        if len(detections) <= 1: return detections
        
        # Sort by area (largest first)
        sorted_dets = sorted(detections, 
                           key=lambda x: (x['width'] * x['height'], x['confidence']), 
                           reverse=True)
        filtered = []
        
        for current in sorted_dets:
            is_dup = False
            curr_area = current['width'] * current['height']
            curr_x2 = current['x'] + current['width']
            curr_y2 = current['y'] + current['height']
            
            for kept in filtered:
                kept_x2 = kept['x'] + kept['width']
                kept_y2 = kept['y'] + kept['height']
                
                # Intersection
                xi1 = max(current['x'], kept['x'])
                yi1 = max(current['y'], kept['y'])
                xi2 = min(curr_x2, kept_x2)
                yi2 = min(curr_y2, kept_y2)
                
                if xi2 > xi1 and yi2 > yi1:
                    intersection = (xi2 - xi1) * (yi2 - yi1)
                    kept_area = kept['width'] * kept['height']
                    smaller_area = min(curr_area, kept_area)
                    ratio = intersection / smaller_area if smaller_area > 0 else 0
                    
                    if ratio > overlap_threshold and curr_area < kept_area:
                        is_dup = True
                        break
            
            if not is_dup:
                filtered.append(current)
                
        return filtered
