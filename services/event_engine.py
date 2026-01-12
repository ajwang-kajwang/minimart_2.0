import time
import json
import os
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional
from services.geometry import GeometryService

@dataclass
class ZoneEvent:
    track_id: int
    zone_name: str
    entry_time: float
    exit_time: float = None
    
    @property
    def duration(self):
        end = self.exit_time or time.time()
        return round(end - self.entry_time, 2)

    def to_natural_language(self):
        return f"Customer {self.track_id} spent {self.duration}s in {self.zone_name}."

class EventEngine:
    def __init__(self, geometry_svc: GeometryService, zones_file="models/zones.json"):
        self.geo = geometry_svc
        self.zones = self._load_zones(zones_file)
        
        # State Tracking
        self.active_events: Dict[int, ZoneEvent] = {} 
        self.completed_events: List[ZoneEvent] = []

    def _load_zones(self, filepath):
        """
        Loads zones defined in WORLD COORDINATES.
        Format: {"Dairy": [[0,0], [100,0], [100,100], [0,100]]}
        """
        if not os.path.exists(filepath):
            print("⚠️ No zones.json found. Event engine idle.")
            return {}
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        parsed_zones = {}
        for name, points in data.items():
            # Convert to numpy array for fast point-in-polygon checks
            parsed_zones[name] = np.array(points, dtype=np.int32)
        return parsed_zones

    def update(self, tracks):
        """
        tracks: List of dicts {'track_id': 1, 'x': 450, 'y': 300, ...} (Pixels)
        """
        current_frame_ids = set()

        for track in tracks:
            tid = track['track_id']
            # Use center of bottom of bounding box (feet location)
            # Assuming 'x' and 'y' passed in are the centroid
            px, py = track['x'], track['y']
            
            # 1. MAGIC: Convert Pixels -> World (e.g., Meters)
            wx, wy = self.geo.pixel_to_world(px, py)
            
            # 2. Determine which zone they are in
            current_zone_name = self._get_zone_for_point(wx, wy)
            
            current_frame_ids.add(tid)
            
            # 3. State Machine Logic
            if tid in self.active_events:
                event = self.active_events[tid]
                
                # Case A: Moved to a different zone
                if event.zone_name != current_zone_name:
                    # Close old event
                    event.exit_time = time.time()
                    self.completed_events.append(event)
                    print(f"📝 EVENT: {event.to_natural_language()}")
                    del self.active_events[tid]
                    
                    # Start new event if entering a valid zone
                    if current_zone_name:
                        self.active_events[tid] = ZoneEvent(tid, current_zone_name, time.time())
            
            elif current_zone_name:
                # Case B: Just entered a zone from "Nowhere"
                self.active_events[tid] = ZoneEvent(tid, current_zone_name, time.time())

    def _get_zone_for_point(self, x, y):
        """
        Checks if World Point (x,y) is inside any defined Zone Polygon
        """
        for name, polygon in self.zones.items():
            # cv2.pointPolygonTest returns > 0 if inside, < 0 if outside
            dist = cv2.pointPolygonTest(polygon, (x, y), False)
            if dist >= 0:
                return name
        return None