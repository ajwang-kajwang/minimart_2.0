"""
Detection Service - TensorRT Accelerated YOLOv8 for Jetson Orin Nano
"""

import cv2
import numpy as np
import os
from typing import List, Dict, Any, Optional
from domain.interfaces import IDetector

# TensorRT imports (Jetson-specific)
try:
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit
    HAS_TENSORRT = True
except ImportError:
    HAS_TENSORRT = False
    print("⚠️  TensorRT not available - will use CPU fallback")

# Ultralytics fallback
try:
    from ultralytics import YOLO
    HAS_ULTRALYTICS = True
except ImportError:
    HAS_ULTRALYTICS = False


class TensorRTDetector:
    """TensorRT-accelerated YOLOv8 detector for Jetson"""
    
    def __init__(self, engine_path: str, confidence_threshold: float = 0.4):
        self.confidence_threshold = confidence_threshold
        self.engine_path = engine_path
        self.logger = trt.Logger(trt.Logger.WARNING)
        
        # Load TensorRT engine
        print(f"🚀 Loading TensorRT engine: {engine_path}")
        with open(engine_path, "rb") as f:
            runtime = trt.Runtime(self.logger)
            self.engine = runtime.deserialize_cuda_engine(f.read())
        
        self.context = self.engine.create_execution_context()
        
        # Allocate buffers
        self._allocate_buffers()
        
        # Get input shape for preprocessing
        self.input_shape = self.engine.get_binding_shape(0)  # e.g., (1, 3, 640, 640)
        self.input_h = self.input_shape[2]
        self.input_w = self.input_shape[3]
        
        print(f"✅ TensorRT engine loaded. Input: {self.input_w}x{self.input_h}")
    
    def _allocate_buffers(self):
        """Allocate GPU buffers for inference"""
        self.inputs = []
        self.outputs = []
        self.bindings = []
        self.stream = cuda.Stream()
        
        for binding in self.engine:
            size = trt.volume(self.engine.get_binding_shape(binding))
            dtype = trt.nptype(self.engine.get_binding_dtype(binding))
            
            # Allocate host and device buffers
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            
            self.bindings.append(int(device_mem))
            
            if self.engine.binding_is_input(binding):
                self.inputs.append({'host': host_mem, 'device': device_mem})
            else:
                self.outputs.append({'host': host_mem, 'device': device_mem})
    
    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame for YOLOv8 input"""
        # Resize with letterbox
        h, w = frame.shape[:2]
        scale = min(self.input_w / w, self.input_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Create letterboxed image
        canvas = np.full((self.input_h, self.input_w, 3), 114, dtype=np.uint8)
        pad_x = (self.input_w - new_w) // 2
        pad_y = (self.input_h - new_h) // 2
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
        
        # Store padding info for postprocessing
        self._scale = scale
        self._pad_x = pad_x
        self._pad_y = pad_y
        
        # Convert to NCHW format and normalize
        blob = canvas.transpose(2, 0, 1).astype(np.float32) / 255.0
        return np.expand_dims(blob, axis=0)
    
    def _postprocess(self, outputs: np.ndarray, orig_shape: tuple) -> List[Dict[str, Any]]:
        """Postprocess YOLOv8 outputs to detection format"""
        detections = []
        
        # YOLOv8 output shape: (1, 84, 8400) for 80 classes
        # Transpose to (8400, 84)
        predictions = outputs[0].T
        
        # Get boxes and scores
        boxes = predictions[:, :4]  # x_center, y_center, width, height
        scores = predictions[:, 4:]  # class scores
        
        # Filter by confidence
        max_scores = np.max(scores, axis=1)
        mask = max_scores > self.confidence_threshold
        
        boxes = boxes[mask]
        scores = scores[mask]
        max_scores = max_scores[mask]
        class_ids = np.argmax(scores, axis=1)
        
        # Filter for person class (class 0)
        person_mask = class_ids == 0
        boxes = boxes[person_mask]
        max_scores = max_scores[person_mask]
        
        orig_h, orig_w = orig_shape[:2]
        
        for box, score in zip(boxes, max_scores):
            # Convert center format to corner format
            cx, cy, w, h = box
            
            # Remove letterbox padding and scale
            x1 = (cx - w/2 - self._pad_x) / self._scale
            y1 = (cy - h/2 - self._pad_y) / self._scale
            x2 = (cx + w/2 - self._pad_x) / self._scale
            y2 = (cy + h/2 - self._pad_y) / self._scale
            
            # Clip to frame bounds
            x1 = max(0, min(x1, orig_w))
            y1 = max(0, min(y1, orig_h))
            x2 = max(0, min(x2, orig_w))
            y2 = max(0, min(y2, orig_h))
            
            detections.append({
                'confidence': float(score),
                'x': float(x1),
                'y': float(y1),
                'width': float(x2 - x1),
                'height': float(y2 - y1)
            })
        
        return self._nms(detections)
    
    def _nms(self, detections: List[Dict], iou_threshold: float = 0.5) -> List[Dict]:
        """Apply Non-Maximum Suppression"""
        if len(detections) <= 1:
            return detections
        
        # Sort by confidence
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        keep = []
        while detections:
            best = detections.pop(0)
            keep.append(best)
            
            detections = [
                d for d in detections
                if self._iou(best, d) < iou_threshold
            ]
        
        return keep
    
    def _iou(self, box1: Dict, box2: Dict) -> float:
        """Calculate IoU between two boxes"""
        x1 = max(box1['x'], box2['x'])
        y1 = max(box1['y'], box2['y'])
        x2 = min(box1['x'] + box1['width'], box2['x'] + box2['width'])
        y2 = min(box1['y'] + box1['height'], box2['y'] + box2['height'])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = box1['width'] * box1['height']
        area2 = box2['width'] * box2['height']
        
        return intersection / (area1 + area2 - intersection)
    
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Run TensorRT inference"""
        # Preprocess
        input_tensor = self._preprocess(frame)
        
        # Copy to GPU
        np.copyto(self.inputs[0]['host'], input_tensor.ravel())
        cuda.memcpy_htod_async(
            self.inputs[0]['device'],
            self.inputs[0]['host'],
            self.stream
        )
        
        # Run inference
        self.context.execute_async_v2(
            bindings=self.bindings,
            stream_handle=self.stream.handle
        )
        
        # Copy results back
        cuda.memcpy_dtoh_async(
            self.outputs[0]['host'],
            self.outputs[0]['device'],
            self.stream
        )
        self.stream.synchronize()
        
        # Postprocess
        output_shape = self.engine.get_binding_shape(1)
        output = self.outputs[0]['host'].reshape(output_shape)
        
        return self._postprocess(output, frame.shape)


class UltralyticsDetector:
    """Fallback detector using Ultralytics YOLO (CUDA or CPU)"""
    
    def __init__(self, model_path: str = "yolov8s.pt", confidence_threshold: float = 0.4):
        self.confidence_threshold = confidence_threshold
        print(f"📦 Loading Ultralytics YOLO: {model_path}")
        self.model = YOLO(model_path)
        
        # Use CUDA if available
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(device)
        print(f"✅ YOLO loaded on {device}")
    
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Run YOLO inference"""
        results = self.model(frame, conf=self.confidence_threshold, classes=[0], verbose=False)
        
        detections = []
        for result in results:
            if result.boxes:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    detections.append({
                        'confidence': float(box.conf[0]),
                        'x': float(x1),
                        'y': float(y1),
                        'width': float(x2 - x1),
                        'height': float(y2 - y1)
                    })
        
        return detections


class DetectionService(IDetector):
    """
    Detection service with automatic backend selection:
    1. TensorRT engine (fastest, Jetson-optimized)
    2. Ultralytics YOLO with CUDA
    3. Ultralytics YOLO CPU fallback
    """
    
    def __init__(self, confidence_threshold: float = 0.4):
        self.confidence_threshold = confidence_threshold
        self.detector: Optional[IDetector] = None
        self._initialize_detector()
    
    def _initialize_detector(self):
        """Initialize the best available detector"""
        
        # Check for TensorRT engine
        engine_path = os.environ.get('TENSORRT_ENGINE', 'models/yolov8s.engine')
        
        if HAS_TENSORRT and os.path.exists(engine_path):
            try:
                self.detector = TensorRTDetector(
                    engine_path,
                    self.confidence_threshold
                )
                return
            except Exception as e:
                print(f"⚠️  TensorRT init failed: {e}")
        
        # Fallback to Ultralytics
        if HAS_ULTRALYTICS:
            model_path = os.environ.get('YOLO_MODEL', 'yolov8s.pt')
            self.detector = UltralyticsDetector(
                model_path,
                self.confidence_threshold
            )
            return
        
        raise RuntimeError("No detection backend available! Install tensorrt or ultralytics.")
    
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Run detection using the initialized backend"""
        return self.detector.detect(frame)
