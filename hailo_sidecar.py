from flask import Flask, request, jsonify
import cv2
import numpy as np
import sys
import os
import logging

# Setup logging to see errors in real-time
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HailoSidecar")

# Import your wrapper
from crowdhuman_hailo_detector import get_hailo_detector

app = Flask(__name__)

print("🚀 Loading Hailo Detector on Host...")
# 1. POINT TO YOUR YOLO FILE
model_path = "models/yolov8s_h8l.hef"

if not os.path.exists(model_path):
    logger.error(f"❌ Error: Model not found at {model_path}")
    sys.exit(1)

# 2. LOAD DETECTOR
try:
    detector = get_hailo_detector(model_name=model_path)
    print(f"✅ Hailo Detector Loaded: {model_path}")
except Exception as e:
    logger.error(f"❌ Failed to load detector: {e}")
    sys.exit(1)

@app.route('/detect', methods=['POST'])
def detect():
    try:
        # A. Receive Image
        if 'image' not in request.files:
            return jsonify({"error": "No image part"}), 400
            
        file = request.files['image']
        npimg = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Failed to decode image"}), 400

        # B. Inference (Wrapped in try/except to prevent crash)
        detections = detector.detect(frame)

        # C. Format Response (Robust Filtering)
        results = []
        for d in detections:
            # 1. Safe Class ID Extraction
            class_id = int(d.get('class_id', -1))
            
            # 2. FILTER: Only allow Class 0 (Person)
            # If we don't do this, it detects chairs/tables and might crash 
            # if the label list doesn't have names for them.
            if class_id == 0:
                results.append({
                    'bbox': [float(x) for x in d['bbox']], # Force float
                    'confidence': float(d['confidence']),  # Force float
                    'class_id': 0,
                    'label': 'person'
                })
        
        return jsonify(results)

    except Exception as e:
        # CATCH ALL CRASHES so the server stays alive
        logger.error(f"⚠️ Inference Error: {e}")
        # Return empty list so Docker keeps running instead of crashing
        return jsonify([]) 

if __name__ == '__main__':
    # Threaded=True allows multiple requests without blocking
    app.run(host='0.0.0.0', port=6000, threaded=True)