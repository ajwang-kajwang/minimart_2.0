import sys
import os
import cv2
import numpy as np

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.geometry import get_store_zones

def visualize_zones_cv2():
    # 1. Create a blank black canvas
    # In production, this would be your camera frame!
    canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Define some nice colors (BGR format for OpenCV)
    colors = [
        (200, 200, 255), # Red-ish
        (200, 255, 200), # Green-ish
        (255, 200, 200), # Blue-ish
        (200, 255, 255), # Yellow-ish
        (255, 255, 200), # Cyan-ish
        (255, 200, 255), # Magenta-ish
    ]

    zones = get_store_zones()
    print(f"Drawing {len(zones)} zones on 1280x720 canvas...")

    # 2. Draw Zones
    for i, zone in enumerate(zones):
        color = colors[i % len(colors)]
        
        # Convert points to numpy array of shape (N, 1, 2) required by polylines
        pts = zone.polygon.reshape((-1, 1, 2))
        
        # A. Draw filled semi-transparent polygon
        overlay = canvas.copy()
        cv2.fillPoly(overlay, [pts], color)
        
        # Blend it (alpha=0.3)
        alpha = 0.3
        canvas = cv2.addWeighted(overlay, alpha, canvas, 1 - alpha, 0)
        
        # B. Draw solid border
        cv2.polylines(canvas, [pts], isClosed=True, color=color, thickness=2)

        # C. Draw Label (Centroid)
        # Calculate center moment
        M = cv2.moments(zone.polygon)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
        else:
            cx, cy = 0, 0

        # Text shadow (black)
        cv2.putText(canvas, zone.name, (cx - 60, cy), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.6, (0, 0, 0), 3, cv2.LINE_AA)
        # Text foreground (white)
        cv2.putText(canvas, zone.name, (cx - 60, cy), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.6, (255, 255, 255), 1, cv2.LINE_AA)

    # 3. Add Title
    cv2.putText(canvas, "MINIMART 2.0 - ZONE CONFIGURATION", (30, 50), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    cv2.putText(canvas, "Press any key to close", (30, 90), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    # 4. Show
    cv2.imshow("Minimart Zone Layout", canvas)
    print("Window open. Press any key to close.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    visualize_zones_cv2()