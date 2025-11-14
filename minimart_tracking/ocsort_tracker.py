#!/usr/bin/env python3
"""
OC-SORT Implementation for Person Tracking
Observation-Centric SORT with enhanced occlusion handling
"""

import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from collections import deque
import time
import math
from scipy.optimize import linear_sum_assignment
from filterpy.kalman import KalmanFilter

@dataclass
class OCTrack:
    """OC-SORT Track object with enhanced occlusion handling"""
    def __init__(self, tlwh, score, track_id=None, image_crop=None):
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
        
        # Enhanced Kalman filter for OC-SORT
        self.kalman_filter = KalmanFilter(dim_x=8, dim_z=4)
        self._init_kalman_filter()
        
        # OC-SORT specific features
        self.observations = deque(maxlen=50)  # Store recent observations
        self.observation_count = 0
        self.velocity_history = deque(maxlen=10)
        
        # History and confidence
        self.history = deque(maxlen=30)
        self.confidence_history = deque(maxlen=10)
        self.confidence_history.append(score)
        
        # Time tracking
        self.time_since_update = 0
        self.first_seen = time.time()
        self.last_seen = time.time()
        
        # Occlusion handling
        self.occlusion_count = 0
        self.max_occlusion_frames = 30
        
        # Appearance features for re-identification
        self.appearance_features: List = []
        self.color_hist_cache = None
        self.last_appearance_update = 0
        
        # Update appearance if image crop provided
        if image_crop is not None:
            self.update_appearance(image_crop)

    def _init_kalman_filter(self):
        """Initialize Kalman filter for OC-SORT with constant velocity model"""
        # State: [x, y, w, h, vx, vy, vw, vh]
        self.kalman_filter.F = np.array([
            [1, 0, 0, 0, 1, 0, 0, 0],
            [0, 1, 0, 0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0, 0, 1, 0],
            [0, 0, 0, 1, 0, 0, 0, 1],
            [0, 0, 0, 0, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 0, 1]
        ])
        
        # Measurement matrix (observe position and size)
        self.kalman_filter.H = np.array([
            [1, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 1, 0, 0, 0, 0]
        ])
        
        # Process noise
        self.kalman_filter.Q *= 0.01
        
        # Measurement noise
        self.kalman_filter.R *= 10
        
        # Initial covariance
        self.kalman_filter.P *= 1000
        
        # Initialize state
        self.kalman_filter.x[:4] = self.tlwh.reshape((4, 1))

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

    def predict(self):
        """Enhanced prediction with observation-centric smoothing"""
        self.kalman_filter.predict()
        
        # OC-SORT: Observation-centric online smoothing
        if len(self.observations) > 1:
            self._apply_oos()
        
        # Update state from Kalman filter
        self.tlwh = self.kalman_filter.x[:4].flatten()
        
        self.time_since_update += 1
        if self.time_since_update > 1:
            self.state = 'lost'
            self.occlusion_count += 1

    def _apply_oos(self):
        """Apply Observation-centric Online Smoothing (OOS)"""
        if len(self.observations) < 2:
            return
        
        # Calculate velocity from recent observations
        recent_obs = list(self.observations)[-5:]  # Last 5 observations
        if len(recent_obs) >= 2:
            velocities = []
            for i in range(1, len(recent_obs)):
                dt = recent_obs[i][1] - recent_obs[i-1][1]  # time difference
                if dt > 0:
                    pos_curr = np.array(recent_obs[i][0][:2])
                    pos_prev = np.array(recent_obs[i-1][0][:2])
                    velocity = (pos_curr - pos_prev) / dt
                    velocities.append(velocity)
            
            if velocities:
                avg_velocity = np.mean(velocities, axis=0)
                # Smooth the velocity in Kalman filter
                self.kalman_filter.x[4:6] = avg_velocity.reshape((2, 1))

    def update(self, new_track, frame_id):
        """Update track with new detection"""
        self.tlwh = new_track.tlwh
        self.score = new_track.score
        self.frame_id = frame_id
        self.tracklet_len += 1
        self.last_seen = time.time()
        self.time_since_update = 0
        self.occlusion_count = 0
        
        # Update Kalman filter
        measurement = self.tlwh.reshape((4, 1))
        self.kalman_filter.update(measurement)
        
        # Store observation for OOS
        self.observations.append((self.tlwh.copy(), time.time()))
        self.observation_count += 1
        
        # Add to history
        self.history.append(self.center)
        self.confidence_history.append(self.score)
        
        if self.state == 'new':
            self.state = 'tracked'
        elif self.state == 'lost':
            self.state = 'tracked'  # Re-acquired
        
        self.is_activated = True

    def update_appearance(self, image_crop):
        """Update appearance features from image crop"""
        if image_crop is None or image_crop.size == 0:
            return
        
        try:
            # Calculate color histogram (HSV)
            if len(image_crop.shape) == 3:
                hsv = cv2.cvtColor(image_crop, cv2.COLOR_BGR2HSV)
                hist_h = cv2.calcHist([hsv], [0], None, [50], [0, 180])
                hist_s = cv2.calcHist([hsv], [1], None, [60], [0, 256])
                hist_v = cv2.calcHist([hsv], [2], None, [60], [0, 256])
                color_hist = np.concatenate([hist_h.flatten(), hist_s.flatten(), hist_v.flatten()])
                color_hist = color_hist / (np.sum(color_hist) + 1e-6)  # Normalize
            else:
                # Grayscale fallback
                hist = cv2.calcHist([image_crop], [0], None, [256], [0, 256])
                color_hist = hist.flatten() / (np.sum(hist) + 1e-6)
            
            # Store feature (keep only recent ones)
            feature_data = {
                'color_histogram': color_hist,
                'timestamp': time.time()
            }
            self.appearance_features.append(feature_data)
            if len(self.appearance_features) > 5:  # Keep last 5 appearances
                self.appearance_features = self.appearance_features[-5:]
            
            self.last_appearance_update = time.time()
            
        except Exception as e:
            print(f"Warning: Failed to update appearance for track {self.track_id}: {e}")

    def calculate_appearance_similarity(self, other_track) -> float:
        """Calculate appearance similarity with another track"""
        if not self.appearance_features or not other_track.appearance_features:
            return 0.0
        
        max_similarity = 0.0
        
        # Compare with recent appearance features
        for my_feature in self.appearance_features[-2:]:  # Last 2 features
            for other_feature in other_track.appearance_features[-2:]:
                if len(my_feature['color_histogram']) == len(other_feature['color_histogram']):
                    hist_similarity = cv2.compareHist(
                        my_feature['color_histogram'].astype(np.float32),
                        other_feature['color_histogram'].astype(np.float32),
                        cv2.HISTCMP_BHATTACHARYYA
                    )
                    hist_similarity = 1.0 - hist_similarity  # Convert to similarity score
                    max_similarity = max(max_similarity, hist_similarity)
        
        return max_similarity

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

class OCSort:
    """OC-SORT algorithm implementation with enhanced occlusion handling"""
    
    def __init__(self, det_thresh=0.6, max_age=50, min_hits=3, iou_threshold=0.3, 
                 delta_t=3, asso_func="iou", inertia=0.2, use_byte=False):
        """
        Args:
            det_thresh: detection confidence threshold
            max_age: maximum age of track before removal
            min_hits: minimum hits to consider track valid
            iou_threshold: IoU threshold for association
            delta_t: time window for velocity calculation
            asso_func: association function ("iou" or "giou")
            inertia: weight for velocity prediction
            use_byte: whether to use ByteTrack-style low score detection association
        """
        self.det_thresh = det_thresh
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.delta_t = delta_t
        self.asso_func = asso_func
        self.inertia = inertia
        self.use_byte = use_byte
        
        # Tracking state
        self.frame_id = 0
        self.tracks: List[OCTrack] = []
        self.track_id_count = 0
        self.total_tracks_created = 0
        
        # Re-identification
        self.disappeared_tracks: List[OCTrack] = []
        self.reid_matches = 0

    def update(self, detections, scores=None, frame=None):
        """
        Update tracking with new detections using OC-SORT algorithm
        Args:
            detections: List of bounding boxes in format [x1, y1, x2, y2] or tlwh format
            scores: List of detection scores (confidence)
            frame: Current frame for appearance features
        Returns:
            List of active tracks with track IDs
        """
        self.frame_id += 1
        
        # Convert detections to OCTrack objects
        if scores is None:
            scores = [1.0] * len(detections)
        
        detected_stracks = []
        for det, score in zip(detections, scores):
            if len(det) == 4:
                if det[2] > det[0] and det[3] > det[1]:  # tlbr format
                    tlwh = [det[0], det[1], det[2] - det[0], det[3] - det[1]]
                else:  # tlwh format
                    tlwh = det
                    
                if score >= self.det_thresh:
                    # Extract appearance features
                    image_crop = None
                    if frame is not None:
                        image_crop = self._extract_crop(frame, det)
                    
                    track = OCTrack(tlwh, score, image_crop=image_crop)
                    detected_stracks.append(track)
        
        # Separate by confidence
        high_score_dets = [t for t in detected_stracks if t.score >= self.det_thresh]
        if self.use_byte:
            low_score_dets = [t for t in detected_stracks if t.score < self.det_thresh and t.score >= 0.1]
        else:
            low_score_dets = []
        
        # Predict all tracks
        for track in self.tracks:
            track.predict()
        
        # First association - high confidence detections
        matched, unmatched_dets, unmatched_trks = self._associate(
            self.tracks, high_score_dets
        )
        
        # Update matched tracks
        for m in matched:
            track = self.tracks[m[0]]
            det = high_score_dets[m[1]]
            track.update(det, self.frame_id)
            
            # Update appearance features
            if frame is not None:
                crop = self._extract_crop(frame, det.tlbr)
                track.update_appearance(crop)
        
        # Handle unmatched tracks
        for i in unmatched_trks:
            track = self.tracks[i]
            if track.occlusion_count < track.max_occlusion_frames:
                track.mark_lost()
            else:
                track.mark_removed()
                if track.observation_count >= self.min_hits:
                    self.disappeared_tracks.append(track)
        
        # Second association with low score detections (if using ByteTrack style)
        if self.use_byte and len(low_score_dets) > 0:
            unmatched_dets_low = [high_score_dets[i] for i in unmatched_dets] + low_score_dets
            lost_tracks = [t for t in self.tracks if t.state == 'lost']
            
            matched_lost, final_unmatched_dets, _ = self._associate(
                lost_tracks, unmatched_dets_low, iou_threshold=0.5
            )
            
            # Update matched lost tracks
            for m in matched_lost:
                track = lost_tracks[m[0]]
                det = unmatched_dets_low[m[1]]
                track.update(det, self.frame_id)
                track.state = 'tracked'
                
                if frame is not None:
                    crop = self._extract_crop(frame, det.tlbr)
                    track.update_appearance(crop)
        else:
            final_unmatched_dets = unmatched_dets
        
        # Re-identification with disappeared tracks
        remaining_unmatched_dets = []
        for det_idx in final_unmatched_dets:
            det = high_score_dets[det_idx] if det_idx < len(high_score_dets) else low_score_dets[det_idx - len(high_score_dets)]
            
            best_match = None
            best_similarity = 0
            
            # Check disappeared tracks for re-identification
            for disappeared_track in self.disappeared_tracks[:]:
                pos_distance = self._calculate_position_distance(det.center, disappeared_track.center)
                if pos_distance < 200:  # Within reasonable distance
                    appearance_sim = disappeared_track.calculate_appearance_similarity(det)
                    
                    # Combined similarity
                    combined_sim = appearance_sim * 0.8 + (1 - min(pos_distance / 200, 1)) * 0.2
                    
                    if combined_sim > best_similarity and combined_sim > 0.6:
                        best_similarity = combined_sim
                        best_match = disappeared_track
            
            if best_match:
                # Re-identify the track
                best_match.update(det, self.frame_id)
                best_match.state = 'tracked'
                best_match.occlusion_count = 0
                
                # Update appearance
                if frame is not None:
                    crop = self._extract_crop(frame, det.tlbr)
                    best_match.update_appearance(crop)
                
                self.tracks.append(best_match)
                self.disappeared_tracks.remove(best_match)
                self.reid_matches += 1
                
                print(f"✅ Re-identified person: Track ID {best_match.track_id} (similarity: {best_similarity:.2f})")
            else:
                remaining_unmatched_dets.append(det_idx)
        
        # Create new tracks for remaining unmatched detections
        for i in remaining_unmatched_dets:
            if i < len(high_score_dets):
                det = high_score_dets[i]
            else:
                det = low_score_dets[i - len(high_score_dets)]
            
            if det.score >= self.det_thresh:
                new_track = OCTrack(det.tlwh, det.score)
                new_track.activate(self.frame_id, self._next_id())
                
                if frame is not None:
                    crop = self._extract_crop(frame, det.tlbr)
                    new_track.update_appearance(crop)
                
                self.tracks.append(new_track)
                self.total_tracks_created += 1
        
        # Clean up tracks
        self.tracks = [t for t in self.tracks if t.state != 'removed']
        
        # Clean up old disappeared tracks
        self.disappeared_tracks = [
            t for t in self.disappeared_tracks 
            if self.frame_id - t.frame_id <= self.max_age
        ]
        
        # Return active tracks
        return [t for t in self.tracks if t.state == 'tracked' and t.observation_count >= self.min_hits]

    def _associate(self, tracks, detections, iou_threshold=None):
        """Associate tracks with detections using Hungarian algorithm"""
        if iou_threshold is None:
            iou_threshold = self.iou_threshold
            
        if len(tracks) == 0 or len(detections) == 0:
            return [], list(range(len(detections))), list(range(len(tracks)))
        
        # Calculate IoU matrix
        iou_matrix = np.zeros((len(tracks), len(detections)), dtype=np.float32)
        for t, track in enumerate(tracks):
            for d, det in enumerate(detections):
                iou_matrix[t, d] = self._iou(track.tlbr, det.tlbr)
        
        # Hungarian algorithm
        row_indices, col_indices = linear_sum_assignment(-iou_matrix)
        
        # Filter matches by IoU threshold
        matched_indices = []
        unmatched_tracks = list(range(len(tracks)))
        unmatched_detections = list(range(len(detections)))
        
        for row, col in zip(row_indices, col_indices):
            if iou_matrix[row, col] >= iou_threshold:
                matched_indices.append([row, col])
                unmatched_tracks.remove(row)
                unmatched_detections.remove(col)
        
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

    def _extract_crop(self, frame, bbox):
        """Extract person crop from frame for appearance features"""
        if frame is None:
            return None
        
        try:
            x1, y1, x2, y2 = [int(coord) for coord in bbox]
            
            # Clip to frame boundaries
            h, w = frame.shape[:2]
            x1 = max(0, min(x1, w-1))
            y1 = max(0, min(y1, h-1))
            x2 = max(x1+1, min(x2, w))
            y2 = max(y1+1, min(y2, h))
            
            # Extract crop
            crop = frame[y1:y2, x1:x2].copy()
            
            # Resize if too small for reliable features
            if crop.shape[0] < 32 or crop.shape[1] < 16:
                crop = cv2.resize(crop, (32, 64))
            
            return crop
            
        except Exception as e:
            print(f"Warning: Failed to extract crop: {e}")
            return None

    def _calculate_position_distance(self, pos1, pos2):
        """Calculate distance between two positions"""
        if isinstance(pos1, (list, tuple)) and isinstance(pos2, (list, tuple)):
            return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
        return float('inf')

    def _next_id(self):
        """Get next track ID"""
        self.track_id_count += 1
        return self.track_id_count

    def get_active_tracks(self):
        """Get currently active tracks"""
        return [t for t in self.tracks if t.state == 'tracked' and t.is_activated]

    def get_track_count(self):
        """Get total number of tracks created"""
        return self.total_tracks_created

    def get_reid_stats(self):
        """Get re-identification statistics"""
        return {
            'total_reid_matches': self.reid_matches,
            'active_tracks': len([t for t in self.tracks if t.state == 'tracked']),
            'disappeared_tracks': len(self.disappeared_tracks),
            'lost_tracks': len([t for t in self.tracks if t.state == 'lost'])
        }

    def reset(self):
        """Reset tracker state"""
        self.frame_id = 0
        self.tracks = []
        self.disappeared_tracks = []
        self.track_id_count = 0
        self.total_tracks_created = 0
        self.reid_matches = 0

# Test function
def test_ocsort():
    """Test OC-SORT implementation"""
    tracker = OCSort(det_thresh=0.6, use_byte=True)
    
    # Simulate a person disappearing and reappearing with occlusion
    test_sequence = [
        # Frame 1-3: Person visible
        [[[100, 100, 200, 200]], [0.9]],
        [[[105, 105, 205, 205]], [0.9]],
        [[[110, 110, 210, 210]], [0.8]],
        
        # Frame 4-8: Person occluded/disappears
        [[], []],
        [[], []],
        [[], []],
        [[], []],
        [[], []],
        
        # Frame 9: Person reappears (should re-identify)
        [[[115, 115, 215, 215]], [0.9]],
        [[[120, 120, 220, 220]], [0.9]],
    ]
    
    print("Testing OC-SORT Tracker:")
    for frame_idx, (dets, scores) in enumerate(test_sequence):
        tracks = tracker.update(dets, scores)
        reid_stats = tracker.get_reid_stats()
        
        print(f"Frame {frame_idx + 1}: {len(tracks)} active, "
              f"ReID matches: {reid_stats['total_reid_matches']}, "
              f"Disappeared: {reid_stats['disappeared_tracks']}")
        
        for track in tracks:
            print(f"  Track ID: {track.track_id}, Pos: {track.center}, State: {track.state}")

if __name__ == "__main__":
    test_ocsort()