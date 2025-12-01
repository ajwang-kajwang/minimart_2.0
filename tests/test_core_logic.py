import pytest
import numpy as np
from services.tracking import TrackingService
from services.geometry import GeometryService

# 1. Test Tracking Logic
def test_tracker_creates_id():
    tracker = TrackingService(max_distance=100)
    
    # Simulate a detection at (100, 100)
    detections = [{'x': 100, 'y': 100, 'width': 50, 'height': 100, 'confidence': 0.9}]
    tracks = tracker.update(detections)
    
    assert len(tracks) == 1
    assert tracks[0]['id'] == 1
    assert tracks[0]['active'] == True

def test_tracker_maintains_id():
    tracker = TrackingService(max_distance=100)
    
    # Frame 1
    tracker.update([{'x': 100, 'y': 100, 'width': 50, 'height': 100, 'confidence': 0.9}])
    
    # Frame 2 (Moved slightly)
    tracks = tracker.update([{'x': 105, 'y': 100, 'width': 50, 'height': 100, 'confidence': 0.9}])
    
    assert len(tracks) == 1
    assert tracks[0]['id'] == 1  # Should still be ID 1

# 2. Test Geometry Logic (Coordinate Mapping)
def test_geometry_service_loads():
    # We can test resilience to missing files
    geo = GeometryService("non_existent_file.json")
    result = geo.pixel_to_world((100, 100))
    assert result == (0.0, 0.0) # Should return default safe values