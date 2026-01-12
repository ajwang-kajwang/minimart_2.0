#!/usr/bin/env python3
"""
Direct CrowdHuman HAILO8L Detector
Uses the local HEF file directly with HailoRT
"""

import cv2
import numpy as np
import hailo_platform as hailo
import time
from typing import List, Dict, Optional, Tuple

class CrowdHumanHailoDetector:
    def __init__(self, hef_path: str = "models/yolo_v8_crowdhuman--640x640_quant_hailort_multidevice_1.hef"):
        """
        Initialize CrowdHuman HAILO8L detector
        
        Args:
            hef_path (str): Path to the HEF model file
        """
        self.hef_path = hef_path
        self.device = None
        self.network_group = None
        self.input_vstream_info = None
        self.output_vstream_info = None
        self.input_shape = (640, 640, 3)
        self.class_names = ["person"]  # CrowdHuman is person-focused
        
        print(f"🚀 Initializing CrowdHuman HAILO8L detector...")
        self.initialize_device()
    
    def initialize_device(self):
        """Initialize HAILO8L device and load CrowdHuman model"""
        try:
            print(f"📂 Loading CrowdHuman HEF: {self.hef_path}")
            
            # Load HEF file
            self.hef = hailo.HEF(self.hef_path)
            
            # Create device
            self.device = hailo.VDevice()
            print(f"✅ Connected to Hailo device")
            
            # Configure network group
            configure_params = hailo.ConfigureParams.create_from_hef(
                hef=self.hef, 
                interface=hailo.HailoStreamInterface.PCIe
            )
            self.network_group = self.device.configure(self.hef, configure_params)[0]
            
            # Get input/output stream info
            self.input_vstream_info = self.hef.get_input_vstream_infos()[0]
            self.output_vstream_infos = self.hef.get_output_vstream_infos()
            
            # Get input shape
            self.input_shape = self.input_vstream_info.shape
            print(f"📐 Input shape: {self.input_shape}")
            print(f"📤 Output streams: {len(self.output_vstream_infos)}")
            
            print("✅ CrowdHuman HAILO8L detector initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing CrowdHuman detector: {e}")
            return False
    
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for CrowdHuman inference
        
        Args:
            frame: Input BGR frame
            
        Returns:
            Preprocessed frame ready for inference
        """
        # Get target dimensions from model input
        height, width = self.input_shape[1], self.input_shape[2]
        
        # Resize frame maintaining aspect ratio
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(frame_rgb, (width, height))
        
        # Convert to uint8 (CrowdHuman model expects UINT8 input)
        if resized.dtype != np.uint8:
            resized = resized.astype(np.uint8)
        
        # Reshape for model input: HWC format
        return resized
    
    def postprocess_detections(self, outputs: List[np.ndarray], 
                             original_shape: Tuple[int, int],
                             conf_threshold: float = 0.5) -> List[Dict]:
        """
        Post-process CrowdHuman YOLO outputs
        
        Args:
            outputs: Raw model outputs (NMS post-processed)
            original_shape: Original frame shape (height, width)
            conf_threshold: Confidence threshold
            
        Returns:
            List of detection dictionaries
        """
        detections = []
        
        try:
            # CrowdHuman model has built-in NMS, so outputs are already processed
            if not outputs or len(outputs) == 0:
                return detections
            
            output = outputs[0] if isinstance(outputs, list) else outputs
            
            # Handle Hailo NMS output format
            if hasattr(output, 'shape') and len(output.shape) > 0:
                # NMS output typically contains structured detections
                for detection in output:
                    if len(detection) >= 6:  # [x1, y1, x2, y2, confidence, class_id]
                        x1, y1, x2, y2, confidence, class_id = detection[:6]
                        
                        if confidence >= conf_threshold:
                            # Scale coordinates to original frame size
                            orig_height, orig_width = original_shape
                            x1 = int(x1 * orig_width / self.input_shape[2])
                            y1 = int(y1 * orig_height / self.input_shape[1])
                            x2 = int(x2 * orig_width / self.input_shape[2])
                            y2 = int(y2 * orig_height / self.input_shape[1])
                            
                            # Create detection dictionary
                            detection_dict = {
                                'bbox': [x1, y1, x2, y2],
                                'confidence': float(confidence),
                                'class_id': int(class_id),
                                'class_name': self.class_names[int(class_id)] if int(class_id) < len(self.class_names) else 'person'
                            }
                            
                            detections.append(detection_dict)
        
        except Exception as e:
            print(f"⚠️ Error in postprocessing: {e}")
            return []
        
        return detections
    
    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        Perform CrowdHuman detection on frame
        
        Args:
            frame: Input BGR frame
            
        Returns:
            List of detection dictionaries
        """
        try:
            if self.device is None or self.network_group is None:
                return []
            
            # Preprocess frame
            input_data = self.preprocess_frame(frame)
            
            # Run inference
            with self.network_group.activate():
                # Create input dictionary
                input_dict = {self.input_vstream_info.name: input_data}
                
                # Perform inference
                outputs = self.network_group.infer(input_dict)
                
                # Post-process results
                detections = self.postprocess_detections(
                    list(outputs.values()), 
                    frame.shape[:2]
                )
                
                return detections
                
        except Exception as e:
            print(f"❌ CrowdHuman detection error: {e}")
            return []
    
    def get_fps_info(self) -> str:
        """Return FPS information"""
        return "CrowdHuman HAILO8L Hardware Accelerated"
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.network_group:
                self.network_group.release()
            if self.device:
                self.device.release()
            print("🧹 CrowdHuman detector cleaned up")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

# Global instance management
_detector_instance = None

def get_hailo_detector(model_name: str = None, cv2_ref_passed=None, np_ref_passed=None) -> Optional[CrowdHumanHailoDetector]:
    """Get or create singleton CrowdHuman detector"""
    global _detector_instance
    
    if _detector_instance is None:
        _detector_instance = CrowdHumanHailoDetector()
        if not _detector_instance.device:
            _detector_instance = None
    
    return _detector_instance

def cleanup_hailo():
    """Clean up CrowdHuman resources"""
    global _detector_instance
    
    if _detector_instance:
        _detector_instance.cleanup()
        _detector_instance = None

def test_crowdhuman_detector():
    """Test the CrowdHuman detector"""
    try:
        detector = CrowdHumanHailoDetector()
        
        # Create test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Run detection
        start_time = time.time()
        detections = detector.detect(test_frame)
        inference_time = time.time() - start_time
        
        print(f"🎯 CrowdHuman detection completed in {inference_time:.4f}s")
        print(f"📊 Found {len(detections)} detections")
        
        detector.cleanup()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_crowdhuman_detector()