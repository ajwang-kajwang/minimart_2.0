"""
Geometry Service - Loads Store Layout from JSON
"""
import json
import os
import numpy as np
import cv2
from typing import List, Tuple

class Zone:
    def __init__(self, data: dict):
        self.id = data['id']
        self.name = data['name']
        self.description = data['description']
        self.type = data.get('type', 'aisle')
        # Convert list of lists to numpy array
        self.polygon = np.array(data['polygon'], dtype=np.int32)
        
    def contains(self, point: Tuple[int, int]) -> bool:
        return cv2.pointPolygonTest(self.polygon, point, False) >= 0

def get_store_zones() -> List[Zone]:
    """Loads zones from config/zones.json"""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    config_path = os.path.join(base_dir, 'config', 'zones.json')
    
    # Create default if missing (Fallback for safety)
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