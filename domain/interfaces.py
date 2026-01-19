"""
Domain Interfaces - SOLID Architecture
Abstract base classes defining contracts for services
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional, List, Dict, Any
import numpy as np


class ICameraSource(ABC):
    """Interface for camera hardware abstraction"""
    
    @abstractmethod
    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Capture a single frame from the camera.
        
        Returns:
            Tuple of (success: bool, frame: np.ndarray or None)
        """
        pass
    
    @abstractmethod
    def release(self) -> None:
        """Release camera resources"""
        pass


class IDetector(ABC):
    """Interface for object detection"""
    
    @abstractmethod
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Perform object detection on a frame.
        
        Args:
            frame: BGR image as numpy array
            
        Returns:
            List of detections, each containing:
            - confidence: float
            - x, y: top-left corner
            - width, height: bounding box dimensions
        """
        pass


class ITracker(ABC):
    """Interface for object tracking"""
    
    @abstractmethod
    def update(self, detections: List[Dict[str, Any]], frame_shape: Tuple[int, int]) -> List[Dict[str, Any]]:
        """
        Update tracker with new detections.
        
        Args:
            detections: List of detection dictionaries
            frame_shape: (height, width) of the frame
            
        Returns:
            List of tracked objects with persistent IDs
        """
        pass
