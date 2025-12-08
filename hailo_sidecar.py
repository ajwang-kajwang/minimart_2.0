from flask import Flask, request, jsonify
import cv2
import numpy as np
import sys
import os

# Import your existing Hailo wrapper
from crowdhuman_hailo_detector import get_hailo_detector

app = Flask(__name__)

# Initialize the detector once on startup
print("🚀 Loading Hailo Detector on Host...")
# Ensure we point to the correct model path on the host
model_path = "/home/icp/minimart_2.0/models/crowdhuman.hef"

if not os.path.exists(model_path):
    print(f"❌ Error: Model not found at {model_path}")
    sys.exit(1)

detector = get_hailo_detector(model_path)
print("✅ Hailo Detector Ready and Listening on Port 6000")

@app.route('/detect', methods=['POST'])
def detect():
    try:
        # 1. Receive Image
        file = request.files['image']
        npimg = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        # 2. Inference (Hardware Accel)
        detections = detector.detect(frame)

        # 3. Format Response
        results = []
        for d in detections:
            # Convert numpy/custom types to standard Python types for JSON
            results.append({
                'bbox': [float(x) for x in d['bbox']],
                'confidence': float(d['confidence']),
                'class_id': int(d['class_id'])
            })
        
        return jsonify(results)
    except Exception as e:
        print(f"Inference Error: {e}")
        return jsonify([]), 500

if __name__ == '__main__':
    # Listen on all interfaces so Docker can reach it
    app.run(host='0.0.0.0', port=6000, threaded=True)
