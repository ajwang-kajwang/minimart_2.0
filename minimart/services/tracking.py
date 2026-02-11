import numpy as np
import math
import time
from domain.interfaces import ITracker

class TrackingService(ITracker):
    def __init__(self, max_distance=150, max_age=30):
        # Original PersonTracker logic variables
        self.tracks = {}
        self.next_id = 1
        self.max_distance = max_distance
        self.max_age = max_age

    def _calculate_distance(self, box1, box2):
        """Euclidean distance between centers"""
        c1 = ((box1[0] + box1[2])/2, (box1[1] + box1[3])/2)
        c2 = ((box2[0] + box2[2])/2, (box2[1] + box2[3])/2)
        return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

    def _calculate_iou(self, box1, box2):
        """IoU Calculation extracted from original code"""
        x1, y1, x2, y2 = box1
        x3, y3, x4, y4 = box2
        xi1, yi1 = max(x1, x3), max(y1, y3)
        xi2, yi2 = min(x2, x4), min(y2, y4)
        
        if xi2 <= xi1 or yi2 <= yi1: return 0
        
        inter = (xi2 - xi1) * (yi2 - yi1)
        area1 = (x2 - x1) * (y2 - y1)
        area2 = (x4 - x3) * (y4 - y3)
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0

    def update(self, detections: list) -> list:
        # Age existing tracks
        for tid in list(self.tracks.keys()):
            self.tracks[tid]['age'] += 1
            self.tracks[tid]['active'] = False
            
        # Remove dead tracks
        for tid in list(self.tracks.keys()):
            if self.tracks[tid]['age'] > self.max_age:
                del self.tracks[tid]

        if not detections:
            return self._format_results()

        # Convert to list format [x1, y1, x2, y2, conf]
        det_boxes = []
        for d in detections:
            det_boxes.append([
                d['x'], d['y'], 
                d['x'] + d['width'], 
                d['y'] + d['height'], 
                d['confidence']
            ])

        # Association Logic (Greedy assignment from original code)
        track_ids = list(self.tracks.keys())
        assigned_tracks = set()
        assigned_detections = set()

        if track_ids:
            cost_matrix = np.zeros((len(track_ids), len(det_boxes)))
            for i, tid in enumerate(track_ids):
                t_box = self.tracks[tid]['box']
                for j, d_box in enumerate(det_boxes):
                    dist = self._calculate_distance(t_box[:4], d_box[:4])
                    iou = self._calculate_iou(t_box[:4], d_box[:4])
                    cost_matrix[i, j] = dist * (1 - iou * 0.7)

            # Greedy match
            for _ in range(min(len(track_ids), len(det_boxes))):
                min_cost = float('inf')
                bt, bd = -1, -1
                for i in range(len(track_ids)):
                    if i in assigned_tracks: continue
                    for j in range(len(det_boxes)):
                        if j in assigned_detections: continue
                        if cost_matrix[i, j] < min_cost and cost_matrix[i, j] < self.max_distance:
                            min_cost = cost_matrix[i, j]
                            bt, bd = i, j
                
                if bt != -1:
                    assigned_tracks.add(bt)
                    assigned_detections.add(bd)
                    # Update track
                    tid = track_ids[bt]
                    self.tracks[tid]['box'] = det_boxes[bd]
                    self.tracks[tid]['age'] = 0
                    self.tracks[tid]['active'] = True

        # Create new tracks
        for i, det in enumerate(det_boxes):
            if i not in assigned_detections:
                tid = self.next_id
                self.next_id += 1
                self.tracks[tid] = {
                    'box': det, 'age': 0, 'active': True,
                    'color': tuple(map(int, np.random.randint(50, 255, 3)))
                }

        return self._format_results()

    def _format_results(self):
        """Format tracks to match legacy output structure"""
        results = []
        for tid, t in self.tracks.items():
            if t['active'] or t['age'] <= 5:
                box = t['box']
                results.append({
                    'id': tid,
                    'x': box[0],
                    'y': box[1],
                    'width': box[2] - box[0],
                    'height': box[3] - box[1],
                    'confidence': box[4],
                    'active': t['active'],
                    'age': t['age'],
                    'color': t['color']
                })
        return results
