"""
Geometry Service - Coordinate transformation and calibration
"""

import json
import os
import numpy as np
from typing import Dict, Any, Optional, Tuple


class GeometryService:
    """
    Handles coordinate transformation from pixel space to real-world coordinates.
    Uses perspective transformation with calibration points.
    """
    
    def __init__(self, calibration_file: str = "coordinate_calibration.json"):
        self.calibration_file = calibration_file
        self.transform_matrix: Optional[np.ndarray] = None
        self.inverse_matrix: Optional[np.ndarray] = None
        self.is_calibrated = False
        
        self._load_calibration()
    
    def _load_calibration(self):
        """Load calibration from file if exists"""
        if os.path.exists(self.calibration_file):
            try:
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)
                
                if 'transform_matrix' in data:
                    self.transform_matrix = np.array(data['transform_matrix'])
                    self.inverse_matrix = np.linalg.inv(self.transform_matrix)
                    self.is_calibrated = True
                    print(f"✅ Loaded calibration from {self.calibration_file}")
            except Exception as e:
                print(f"⚠️  Failed to load calibration: {e}")
    
    def calibrate(self, pixel_points: np.ndarray, world_points: np.ndarray):
        """
        Calibrate using corresponding points.
        
        Args:
            pixel_points: Nx2 array of pixel coordinates
            world_points: Nx2 array of world coordinates (e.g., meters)
        """
        if len(pixel_points) < 4 or len(world_points) < 4:
            raise ValueError("Need at least 4 calibration points")
        
        # Compute perspective transform
        self.transform_matrix, _ = cv2.findHomography(
            pixel_points.astype(np.float32),
            world_points.astype(np.float32)
        )
        self.inverse_matrix = np.linalg.inv(self.transform_matrix)
        self.is_calibrated = True
        
        # Save calibration
        self._save_calibration()
    
    def _save_calibration(self):
        """Save calibration to file"""
        try:
            data = {
                'transform_matrix': self.transform_matrix.tolist()
            }
            with open(self.calibration_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"✅ Saved calibration to {self.calibration_file}")
        except Exception as e:
            print(f"⚠️  Failed to save calibration: {e}")
    
    def pixel_to_world(self, x: float, y: float) -> Tuple[float, float]:
        """
        Convert pixel coordinates to world coordinates.
        
        Returns (x, y) in world units if calibrated, else returns pixel coords.
        """
        if not self.is_calibrated or self.transform_matrix is None:
            return (x, y)
        
        point = np.array([[x, y]], dtype=np.float32)
        point = np.array([point])
        
        transformed = cv2.perspectiveTransform(point, self.transform_matrix)
        
        return (float(transformed[0][0][0]), float(transformed[0][0][1]))
    
    def world_to_pixel(self, x: float, y: float) -> Tuple[float, float]:
        """
        Convert world coordinates back to pixel coordinates.
        """
        if not self.is_calibrated or self.inverse_matrix is None:
            return (x, y)
        
        point = np.array([[x, y]], dtype=np.float32)
        point = np.array([point])
        
        transformed = cv2.perspectiveTransform(point, self.inverse_matrix)
        
        return (float(transformed[0][0][0]), float(transformed[0][0][1]))
    
    def transform_tracks(self, tracks: list) -> list:
        """
        Add world coordinates to track data.
        """
        for track in tracks:
            if 'centroid_x' in track and 'centroid_y' in track:
                world_x, world_y = self.pixel_to_world(
                    track['centroid_x'], 
                    track['centroid_y']
                )
                track['world_x'] = world_x
                track['world_y'] = world_y
        
        return tracks


# Import cv2 only when needed (avoid import error if not installed)
try:
    import cv2
except ImportError:
    cv2 = None
    print("⚠️  OpenCV not available - geometry calibration disabled")
