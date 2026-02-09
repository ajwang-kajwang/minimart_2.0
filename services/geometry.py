"""
Geometry Service - Unified (Homography + Zones)
Handles both 3D World Mapping and 2D Semantic Zones.
"""
import json
import os
import numpy as np
import cv2
from typing import List, Tuple

# ==========================================
# PART 1: HOMOGRAPHY (The Pi's Existing Logic)
# ==========================================
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
            if isinstance(pixel_points, (list, tuple)):
                points = np.array([[pixel_points]], dtype=np.float32)
            else:
                points = pixel_points.reshape(-1, 1, 2).astype(np.float32)
            
            # Apply transformation
            world_points = cv2.perspectiveTransform(points, self.homography_matrix)
            result = world_points.reshape(-1, 2)[0]
            return (float(result[0]), float(result[1]))
            
        except Exception as e:
            return (0.0, 0.0)

# ==========================================
# PART 2: SEMANTIC ZONES (The Jetson's Logic)
# ==========================================
class Zone:
    def __init__(self, data: dict):
        self.id = data.get('id', 'unknown')
        self.name = data.get('name', 'Unnamed Zone')
        self.description = data.get('description', '')
        self.type = data.get('type', 'aisle')
        # Convert list of lists to numpy array
        self.polygon = np.array(data['polygon'], dtype=np.int32)
        
    def contains(self, point: Tuple[int, int]) -> bool:
        # Returns True if point (x,y) is inside the polygon
        return cv2.pointPolygonTest(self.polygon, point, False) >= 0

def get_store_zones() -> List[Zone]:
    """Loads zones from config/zones.json"""
    # Locate config/zones.json relative to this file
    base_dir = os.path.dirname(os.path.dirname(__file__))
    config_path = os.path.join(base_dir, 'config', 'zones.json')
    
    if not os.path.exists(config_path):
        print(f"⚠️ Config not found at {config_path}, returning empty list.")
        return []

    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
            return [Zone(z) for z in data]
    except Exception as e:
        print(f"❌ Error loading zones.json: {e}")
        return []