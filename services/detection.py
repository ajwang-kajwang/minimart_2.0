import os
import sys
import numpy as np
from domain.interfaces import IDetector

# Add root path to find the 'crowdhuman_hailo_detector.py' file
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from crowdhuman_hailo_detector import CrowdHumanHailoDetector
    HAS_HAILO = True
except ImportError:
    HAS_HAILO = False

class DetectionService(IDetector):
    def __init__(self, confidence_threshold: float = 0.5):
        self.detector = None
        self.confidence_threshold = confidence_threshold
        
        # 1. Define the correct model path for Pi 5
        self.model_path = "models/yolov8s_h8l.hef"
        
        # 2. Initialize Hailo Directly
        if HAS_HAILO and os.path.exists(self.model_path):
            print(f"🚀 Initializing Direct Hailo Connection...")
            print(f"📂 Loading Model: {self.model_path}")
            try:
                # FIX: Removed 'confidence' argument from __init__
                self.detector = CrowdHumanHailoDetector(
                    hef_path=self.model_path
                )
                print("✅ Hailo-8L Hardware Connected Successfully")
            except Exception as e:
                print(f"❌ Failed to initialize Hailo Hardware: {e}")
                self.detector = None
        else:
            print(f"❌ Model missing at {self.model_path} or Hailo libs missing.")

    def detect(self, frame: np.ndarray) -> list:
        if self.detector:
            # Direct Hardware Inference
            raw_detections = self.detector.detect(frame)
            
            # FIX: Apply confidence filtering here manually
            filtered_detections = [
                d for d in raw_detections 
                if d.get('confidence', 0) >= self.confidence_threshold
            ]
            return self._filter_overlapping(filtered_detections)
        else:
            return []

    def _filter_overlapping(self, detections, overlap_threshold=0.5):
        """
        Removes duplicate boxes (Non-Maximum Suppression).
        """
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
                    
                    if (intersection / smaller_area if smaller_area > 0 else 0) > overlap_threshold:
                        is_dup = True
                        break
            
            if not is_dup: 
                filtered.append(current)
                
        return filtered