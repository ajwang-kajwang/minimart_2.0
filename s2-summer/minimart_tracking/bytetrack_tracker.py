#!/usr/bin/env python3
"""
ByteTrack Implementation for Person Tracking
Simplified version of ByteTrack algorithm for person detection tracking
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from collections import deque
import time
import math

@dataclass
class STrack:
    """Single Track object for ByteTrack"""
    def __init__(self, tlwh, score, track_id=None):
        # tlwh = top-left-width-height format
        self.tlwh = np.array(tlwh, dtype=np.float32)
        self.score = score
        self.track_id = track_id
        self.is_activated = False
        self.state = 'new'  # 'new', 'tracked', 'lost', 'removed'
        
        # Tracking information
        self.frame_id = 0
        self.tracklet_len = 0
        self.start_frame = 0
        
        # Kalman filter state
        self.mean = None
        self.covariance = None
        
        # History
        self.history = deque(maxlen=30)
        
        # Time tracking
        self.time_since_update = 0
        self.first_seen = time.time()
        self.last_seen = time.time()

    @property 
    def tlbr(self):
        """Convert tlwh to tlbr (top-left-bottom-right)"""
        ret = self.tlwh.copy()
        ret[2:] += ret[:2]
        return ret

    @property
    def center(self):
        """Get center point of bounding box"""
        tlbr = self.tlbr
        return ((tlbr[0] + tlbr[2]) / 2, (tlbr[1] + tlbr[3]) / 2)

    def update(self, new_track, frame_id):
        """Update track with new detection"""
        self.tlwh = new_track.tlwh
        self.score = new_track.score
        self.frame_id = frame_id
        self.tracklet_len += 1
        self.last_seen = time.time()
        self.time_since_update = 0
        
        # Add to history
        self.history.append(self.center)
        
        if self.state == 'new':
            self.state = 'tracked'
        
        self.is_activated = True

    def predict(self):
        """Simple prediction - just increment time since update"""
        self.time_since_update += 1
        if self.time_since_update > 1:
            self.state = 'lost'

    def activate(self, frame_id, track_id):
        """Activate track"""
        self.track_id = track_id
        self.start_frame = frame_id
        self.frame_id = frame_id
        self.is_activated = True
        self.state = 'tracked'

    def mark_lost(self):
        """Mark track as lost"""
        self.state = 'lost'

    def mark_removed(self):
        """Mark track as removed"""
        self.state = 'removed'

class ByteTracker:
    """ByteTrack algorithm implementation"""
    
    def __init__(self, frame_rate=30, track_thresh=0.5, track_buffer=30, match_thresh=0.8, mot20=False):
        self.frame_rate = frame_rate
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.mot20 = mot20
        
        # Tracking state
        self.frame_id = 0
        self.tracked_stracks: List[STrack] = []
        self.lost_stracks: List[STrack] = []
        self.removed_stracks: List[STrack] = []
        
        # ID management
        self.track_id_count = 0
        
        # History for analytics
        self.total_tracks_created = 0

    def update(self, detections, scores=None):
        """
        Update tracking with new detections
        Args:
            detections: List of bounding boxes in format [x1, y1, x2, y2] or tlwh format
            scores: List of detection scores (confidence)
        Returns:
            List of active tracks with track IDs
        """
        self.frame_id += 1
        
        # Convert detections to STrack objects
        if scores is None:
            scores = [1.0] * len(detections)
        
        # Create tracks from detections
        detected_stracks = []
        for det, score in zip(detections, scores):
            if len(det) == 4:
                if det[2] > det[0] and det[3] > det[1]:  # x2 > x1, y2 > y1 (tlbr format)
                    # Convert from tlbr to tlwh
                    tlwh = [det[0], det[1], det[2] - det[0], det[3] - det[1]]
                else:  # Already in tlwh format
                    tlwh = det
                    
                if score >= self.track_thresh:
                    detected_stracks.append(STrack(tlwh, score))

        # Separate detections by score
        if self.mot20:
            # For MOT20, use lower threshold for second association
            high_score_dets = [t for t in detected_stracks if t.score >= self.track_thresh]
            low_score_dets = [t for t in detected_stracks if t.score < self.track_thresh and t.score >= 0.1]
        else:
            high_score_dets = detected_stracks
            low_score_dets = []

        # Update existing tracks
        for track in self.tracked_stracks + self.lost_stracks:
            track.predict()

        # First association - high confidence detections with tracked tracks
        matched, unmatched_dets, unmatched_trks = self._associate(
            self.tracked_stracks, high_score_dets, self.match_thresh
        )

        # Update matched tracks
        for m in matched:
            track = self.tracked_stracks[m[0]]
            det = high_score_dets[m[1]]
            track.update(det, self.frame_id)

        # Second association - unmatched detections with lost tracks
        if len(low_score_dets) > 0:
            unmatched_dets_low = [high_score_dets[i] for i in unmatched_dets] + low_score_dets
        else:
            unmatched_dets_low = [high_score_dets[i] for i in unmatched_dets]

        lost_stracks = [t for t in self.lost_stracks if t.state == 'lost']
        matched_lost, unmatched_dets_final, unmatched_lost = self._associate(
            lost_stracks, unmatched_dets_low, 0.5
        )

        # Update matched lost tracks
        for m in matched_lost:
            track = lost_stracks[m[0]]
            det = unmatched_dets_low[m[1]]
            track.update(det, self.frame_id)
            track.state = 'tracked'

        # Handle unmatched tracks
        for i in unmatched_trks:
            track = self.tracked_stracks[i]
            if track.time_since_update <= 1:
                track.mark_lost()
            else:
                track.mark_removed()

        # Create new tracks from unmatched detections
        for i in unmatched_dets_final:
            det = unmatched_dets_low[i]
            if det.score >= self.track_thresh:
                new_track = STrack(det.tlwh, det.score)
                new_track.activate(self.frame_id, self._next_id())
                self.tracked_stracks.append(new_track)
                self.total_tracks_created += 1

        # Update track states
        self.tracked_stracks = [t for t in self.tracked_stracks if t.state == 'tracked']
        self.lost_stracks = [t for t in self.tracked_stracks + self.lost_stracks if t.state == 'lost']
        self.removed_stracks.extend([t for t in self.tracked_stracks + self.lost_stracks if t.state == 'removed'])

        # Remove old lost tracks
        self.lost_stracks = [t for t in self.lost_stracks if self.frame_id - t.frame_id <= self.track_buffer]

        return self.tracked_stracks

    def _associate(self, tracks, detections, thresh):
        """Associate tracks with detections using IoU"""
        if len(tracks) == 0 or len(detections) == 0:
            return [], list(range(len(detections))), list(range(len(tracks)))

        # Calculate IoU matrix
        iou_matrix = np.zeros((len(tracks), len(detections)), dtype=np.float32)
        for t, track in enumerate(tracks):
            for d, det in enumerate(detections):
                iou_matrix[t, d] = self._iou(track.tlbr, det.tlbr)

        # Hungarian algorithm approximation (greedy matching)
        matched_indices = []
        unmatched_tracks = list(range(len(tracks)))
        unmatched_detections = list(range(len(detections)))

        # Greedy matching based on highest IoU
        while len(unmatched_tracks) > 0 and len(unmatched_detections) > 0:
            # Find maximum IoU
            max_iou = 0
            max_track_idx = -1
            max_det_idx = -1
            
            for t_idx in unmatched_tracks:
                for d_idx in unmatched_detections:
                    if iou_matrix[t_idx, d_idx] > max_iou:
                        max_iou = iou_matrix[t_idx, d_idx]
                        max_track_idx = t_idx
                        max_det_idx = d_idx
            
            # Check if IoU is above threshold
            if max_iou >= thresh:
                matched_indices.append([max_track_idx, max_det_idx])
                unmatched_tracks.remove(max_track_idx)
                unmatched_detections.remove(max_det_idx)
            else:
                break

        return matched_indices, unmatched_detections, unmatched_tracks

    def _iou(self, box1, box2):
        """Calculate Intersection over Union (IoU) of two bounding boxes"""
        # box format: [x1, y1, x2, y2]
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        
        if union <= 0:
            return 0.0
        
        return intersection / union

    def _next_id(self):
        """Get next track ID"""
        self.track_id_count += 1
        return self.track_id_count

    def get_active_tracks(self):
        """Get currently active tracks"""
        return [t for t in self.tracked_stracks if t.is_activated]

    def get_track_count(self):
        """Get total number of tracks created"""
        return self.total_tracks_created

    def reset(self):
        """Reset tracker state"""
        self.frame_id = 0
        self.tracked_stracks = []
        self.lost_stracks = []
        self.removed_stracks = []
        self.track_id_count = 0
        self.total_tracks_created = 0

# Utility functions for integration
def detections_to_tlbr(detections):
    """Convert detection format to tlbr"""
    result = []
    for det in detections:
        if hasattr(det, 'bbox'):
            # Detection object with bbox attribute
            x1, y1, x2, y2 = det.bbox
            result.append([x1, y1, x2, y2])
        elif len(det) == 4:
            # Already a 4-element list/tuple
            result.append(det)
        else:
            print(f"Warning: Unknown detection format: {det}")
    return result

def detections_to_scores(detections):
    """Extract scores from detections"""
    result = []
    for det in detections:
        if hasattr(det, 'confidence'):
            result.append(det.confidence)
        elif hasattr(det, 'score'):
            result.append(det.score)
        else:
            result.append(1.0)  # Default score
    return result

# Test function
def test_bytetrack():
    """Test ByteTrack implementation"""
    tracker = ByteTracker()
    
    # Simulate detections for 3 frames
    test_detections = [
        # Frame 1: 2 detections
        [[[100, 100, 200, 200], [300, 150, 400, 250]], [0.9, 0.8]],
        # Frame 2: 2 detections (moved)
        [[[105, 105, 205, 205], [305, 155, 405, 255]], [0.9, 0.8]],
        # Frame 3: 1 detection (one disappeared)
        [[[110, 110, 210, 210]], [0.9]]
    ]
    
    for frame_idx, (dets, scores) in enumerate(test_detections):
        print(f"\nFrame {frame_idx + 1}")
        tracks = tracker.update(dets, scores)
        
        print(f"Active tracks: {len(tracks)}")
        for track in tracks:
            print(f"  Track ID: {track.track_id}, Score: {track.score:.2f}, "
                  f"Box: {track.tlbr}, State: {track.state}")

if __name__ == "__main__":
    test_bytetrack()