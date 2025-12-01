import json
import numpy as np
import cv2
import os

class GeometryService:
    """
    Handles geometric transformations and coordinate mapping.
    Responsible for converting 2D pixel coordinates to 3D/2D real-world coordinates.
    """
    def __init__(self, calibration_file: str = "coordinate_calibration.json"):
        self.homography_matrix = None
        self.calibration_file = calibration_file
        self._load_calibration()
    
    def _load_calibration(self):
        """Load homography matrix from JSON file"""
        if not os.path.exists(self.calibration_file):
            print(f"⚠️ Calibration file not found: {self.calibration_file}")
            return

        try:
            with open(self.calibration_file, 'r') as f:
                data = json.load(f)
            
            if 'homography_matrix' in data:
                self.homography_matrix = np.array(data['homography_matrix'])
                print(f"✅ Coordinate calibration loaded from {self.calibration_file}")
            else:
                print("❌ Invalid calibration format: 'homography_matrix' key missing")
                
        except Exception as e:
            print(f"❌ Failed to load calibration: {e}")
    
    def pixel_to_world(self, pixel_points) -> tuple:
        """
        Convert pixel coordinates (x, y) to world coordinates.
        Returns: (world_x, world_y) or (0.0, 0.0) if failed
        """
        if self.homography_matrix is None:
            return (0.0, 0.0)
        
        try:
            # Ensure points are in correct format for cv2.perspectiveTransform
            # Input shape must be (N, 1, 2)
            if isinstance(pixel_points, (list, tuple)):
                points = np.array([[pixel_points]], dtype=np.float32)
            else:
                points = pixel_points.reshape(-1, 1, 2).astype(np.float32)
            
            # Apply transformation
            world_points = cv2.perspectiveTransform(points, self.homography_matrix)
            
            # Return flattened result
            result = world_points.reshape(-1, 2)[0]
            return (float(result[0]), float(result[1]))
            
        except Exception as e:
            # Fail silently or log if needed to prevent stream crash
            return (0.0, 0.0)