import cv2
import numpy as np
import os
from ultralytics import YOLO
from domain.interfaces import IDetector

# Import legacy dependency
try:
    from crowdhuman_hailo_detector import get_hailo_detector
    HAS_ENHANCED_DETECTOR = True
except ImportError:
    HAS_ENHANCED_DETECTOR = False

class DetectionService(IDetector):
    def __init__(self, confidence_threshold: float = 0.4):
        self.detector = None
        self.model = None
        self.confidence_threshold = confidence_threshold
        self.use_enhanced = False
        self._initialize_model()

    def _initialize_model(self):
        # 1. Try Enhanced Hailo Detector
        if HAS_ENHANCED_DETECTOR:
            print("🚀 Initializing CrowdHuman YOLO v8 HAILO8L detector...")
            self.detector = get_hailo_detector(
                "yolo_v8_crowdhuman--640x640_quant_hailort_multidevice_1",
                cv2_ref_passed=cv2,
                np_ref_passed=np
            )
            if self.detector:
                self.use_enhanced = True
                print("✅ CrowdHuman YOLO v8 HAILO8L detector loaded")
                return

        # 2. Fallback to Standard YOLO
        self.use_enhanced = False
        model_path = "models/custom_yolo_deployment/custom_yolo.pt"
        if os.path.exists(model_path):
            self.model = YOLO(model_path)
            print("✅ Custom trained YOLOv8s model loaded")
        else:
            self.model = YOLO("yolov8s.pt")
            print("✅ Default YOLOv8s model loaded")

    def detect(self, frame: np.ndarray) -> list:
        raw_detections = []
        
        if self.use_enhanced:
            # Enhanced Hailo Logic
            enhanced_results = self.detector.detect(frame)
            for det in enhanced_results:
                x1, y1, x2, y2 = det.bbox
                raw_detections.append({
                    'confidence': det.confidence,
                    'x': float(x1),
                    'y': float(y1),
                    'width': float(x2 - x1),
                    'height': float(y2 - y1)
                })
        else:
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