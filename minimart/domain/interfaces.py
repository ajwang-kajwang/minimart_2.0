from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

class ICameraSource(ABC):
    """Abstract interface for camera hardware abstraction"""
    
    @abstractmethod
    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Capture a single frame
        Returns: (success, frame)
        """
        pass

    @abstractmethod
    def release(self):
        """Release hardware resources"""
        pass

class IDetector(ABC):
    """Abstract interface for object detection models"""
    
    @abstractmethod
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Perform detection on a frame
        Returns list of dicts: {'x':, 'y':, 'width':, 'height':, 'confidence':}
        """
        pass

class ITracker(ABC):
    """Abstract interface for object tracking algorithms"""
    
    @abstractmethod
    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Update tracks with new detections
        Returns list of track dicts with 'id', 'x', 'y', etc.
        """
        pass