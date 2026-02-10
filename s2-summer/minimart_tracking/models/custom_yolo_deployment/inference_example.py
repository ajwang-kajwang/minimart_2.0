
from ultralytics import YOLO
import cv2

# Load the trained model
model = YOLO('custom_yolo.pt')

# Run inference on an image
results = model('path_to_your_image.jpg')

# Display results
for result in results:
    # Get bounding boxes, classes, and confidence scores
    boxes = result.boxes.xyxy.cpu().numpy()  # x1, y1, x2, y2
    classes = result.boxes.cls.cpu().numpy()
    confidences = result.boxes.conf.cpu().numpy()
    
    print(f"Detected {len(boxes)} objects")
    for i, (box, cls, conf) in enumerate(zip(boxes, classes, confidences)):
        x1, y1, x2, y2 = box
        class_name = model.names[int(cls)]
        print(f"Object {i+1}: {class_name} ({conf:.2f}) at [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}]")
    
    # Plot results
    result.show()
