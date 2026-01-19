"""
Tracking Service - OC-SORT based person tracking
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from domain.interfaces import ITracker


class TrackingService(ITracker):
    """
    Simple centroid-based tracker with persistent IDs.
    Matches detections to existing tracks based on distance.
    """
    
    def __init__(self, max_distance: float = 150, max_disappeared: int = 30):
        self.max_distance = max_distance
        self.max_disappeared = max_disappeared
        self.next_id = 1
        self.tracks: Dict[int, Dict[str, Any]] = {}
        self.disappeared: Dict[int, int] = {}
    
    def _get_centroid(self, detection: Dict[str, Any]) -> Tuple[float, float]:
        """Calculate centroid from detection box"""
        cx = detection['x'] + detection['width'] / 2
        cy = detection['y'] + detection['height'] / 2
        return (cx, cy)
    
    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Euclidean distance between two points"""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def update(self, detections: List[Dict[str, Any]], frame_shape: Tuple[int, int]) -> List[Dict[str, Any]]:
        """
        Update tracks with new detections using Hungarian-style matching.
        
        Args:
            detections: List of detection dictionaries
            frame_shape: (height, width) of the frame
            
        Returns:
            List of tracked objects with persistent IDs
        """
        
        # If no detections, increment disappeared count for all tracks
        if len(detections) == 0:
            for track_id in list(self.disappeared.keys()):
                self.disappeared[track_id] += 1
                self.tracks[track_id]['active'] = False
                
                if self.disappeared[track_id] > self.max_disappeared:
                    del self.tracks[track_id]
                    del self.disappeared[track_id]
            
            return list(self.tracks.values())
        
        # Get centroids for new detections
        new_centroids = [self._get_centroid(d) for d in detections]
        
        # If no existing tracks, create new ones
        if len(self.tracks) == 0:
            for i, detection in enumerate(detections):
                self._register_track(detection, new_centroids[i])
            return list(self.tracks.values())
        
        # Match existing tracks to new detections
        track_ids = list(self.tracks.keys())
        track_centroids = [(self.tracks[tid]['centroid_x'], self.tracks[tid]['centroid_y']) 
                          for tid in track_ids]
        
        # Build distance matrix
        D = np.zeros((len(track_ids), len(new_centroids)))
        for i, tc in enumerate(track_centroids):
            for j, nc in enumerate(new_centroids):
                D[i, j] = self._distance(tc, nc)
        
        # Greedy matching (simple Hungarian alternative)
        used_tracks = set()
        used_detections = set()
        matches = []
        
        # Sort by distance and match greedily
        indices = np.unravel_index(np.argsort(D, axis=None), D.shape)
        for i, j in zip(indices[0], indices[1]):
            if i in used_tracks or j in used_detections:
                continue
            if D[i, j] > self.max_distance:
                continue
            
            matches.append((track_ids[i], j))
            used_tracks.add(i)
            used_detections.add(j)
        
        # Update matched tracks
        for track_id, det_idx in matches:
            detection = detections[det_idx]
            centroid = new_centroids[det_idx]
            
            self.tracks[track_id].update({
                'x': detection['x'],
                'y': detection['y'],
                'width': detection['width'],
                'height': detection['height'],
                'confidence': detection['confidence'],
                'centroid_x': centroid[0],
                'centroid_y': centroid[1],
                'active': True
            })
            self.disappeared[track_id] = 0
        
        # Handle unmatched tracks
        unmatched_track_indices = set(range(len(track_ids))) - used_tracks
        for i in unmatched_track_indices:
            track_id = track_ids[i]
            self.disappeared[track_id] += 1
            self.tracks[track_id]['active'] = False
            
            if self.disappeared[track_id] > self.max_disappeared:
                del self.tracks[track_id]
                del self.disappeared[track_id]
        
        # Register new tracks for unmatched detections
        unmatched_det_indices = set(range(len(detections))) - used_detections
        for j in unmatched_det_indices:
            self._register_track(detections[j], new_centroids[j])
        
        return list(self.tracks.values())
    
    def _register_track(self, detection: Dict[str, Any], centroid: Tuple[float, float]):
        """Register a new track"""
        track_id = self.next_id
        self.next_id += 1
        
        self.tracks[track_id] = {
            'id': track_id,
            'x': detection['x'],
            'y': detection['y'],
            'width': detection['width'],
            'height': detection['height'],
            'confidence': detection['confidence'],
            'centroid_x': centroid[0],
            'centroid_y': centroid[1],
            'active': True
        }
        self.disappeared[track_id] = 0
