import cv2
import numpy as np
import json
import os
from typing import List, Tuple, Optional, Dict

class CameraCalibrator:
    def __init__(self, calib_images_dir: str = "calib_images"):
        self.calib_images_dir = calib_images_dir
        self.camera_matrix = None
        self.dist_coeffs = None
        self.homography_matrix = None
        self.real_world_corners = None
        self.image_corners = None
        
    def load_calibration_images(self) -> List[str]:
        """Load all calibration images from the directory"""
        image_extensions = ['.jpg', '.jpeg', '.png']
        images = []
        
        for file in os.listdir(self.calib_images_dir):
            if any(file.lower().endswith(ext) for ext in image_extensions):
                images.append(os.path.join(self.calib_images_dir, file))
        
        return sorted(images)
    
    def detect_layout_corners(self, image_path: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Detect corners in the layout image based on the coordinate grid
        Returns image corners and corresponding real-world coordinates
        """
        image = cv2.imread(image_path)
        if image is None:
            return None
            
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # For the layout grid image, we'll manually define the corners based on the visible grid
        # This assumes the grid layout image shows the coordinate system
        if "3d_layout_grid_xy.png" in image_path:
            # Define real-world coordinates based on the grid (in meters or your preferred unit)
            # From the image, we can see coordinates (0,100), (100,100), (100,0), (0,0)
            real_world_points = np.array([
                [0, 0],      # Origin (bottom-left in real world)
                [100, 0],    # Bottom-right
                [100, 100],  # Top-right  
                [0, 100]     # Top-left
            ], dtype=np.float32)
            
            # For manual corner detection, we'll use corner detection algorithms
            corners = cv2.goodFeaturesToTrack(gray, maxCorners=4, qualityLevel=0.01, minDistance=100)
            
            if corners is not None and len(corners) >= 4:
                # Sort corners to match our real-world coordinate order
                corners = corners.reshape(-1, 2)
                # Sort by y-coordinate first, then x-coordinate
                corners = corners[np.lexsort((corners[:, 0], corners[:, 1]))]
                
                return corners.astype(np.float32), real_world_points
        
        return None
    
    def calibrate_with_homography(self, image_path: str) -> bool:
        """
        Calibrate camera using homography transformation
        This is suitable for planar scenes like floor layouts
        """
        result = self.detect_layout_corners(image_path)
        if result is None:
            return False
            
        image_corners, real_world_corners = result
        
        if len(image_corners) >= 4 and len(real_world_corners) >= 4:
            # Calculate homography matrix
            self.homography_matrix, _ = cv2.findHomography(
                image_corners, real_world_corners, cv2.RANSAC
            )
            self.image_corners = image_corners
            self.real_world_corners = real_world_corners
            return True
        
        return False
    
    def pixel_to_world_coordinates(self, pixel_points: np.ndarray) -> np.ndarray:
        """
        Convert pixel coordinates to real-world coordinates using homography
        """
        if self.homography_matrix is None:
            raise ValueError("Camera not calibrated. Call calibrate_with_homography first.")
        
        # Ensure points are in the correct format
        if pixel_points.ndim == 1:
            pixel_points = pixel_points.reshape(1, -1)
        
        # Add homogeneous coordinate
        if pixel_points.shape[1] == 2:
            ones = np.ones((pixel_points.shape[0], 1))
            pixel_points_homo = np.hstack([pixel_points, ones])
        else:
            pixel_points_homo = pixel_points
        
        # Apply homography transformation
        world_points_homo = self.homography_matrix @ pixel_points_homo.T
        
        # Convert back to 2D coordinates
        world_points = (world_points_homo[:2] / world_points_homo[2]).T
        
        # Clamp coordinates to valid range (0-100) to prevent out-of-bounds values
        world_points = np.clip(world_points, 0.0, 100.0)
        
        return world_points
    
    def world_to_pixel_coordinates(self, world_points: np.ndarray) -> np.ndarray:
        """
        Convert real-world coordinates to pixel coordinates using inverse homography
        """
        if self.homography_matrix is None:
            raise ValueError("Camera not calibrated. Call calibrate_with_homography first.")
        
        # Use inverse homography
        inv_homography = np.linalg.inv(self.homography_matrix)
        
        # Ensure points are in the correct format
        if world_points.ndim == 1:
            world_points = world_points.reshape(1, -1)
        
        # Add homogeneous coordinate
        if world_points.shape[1] == 2:
            ones = np.ones((world_points.shape[0], 1))
            world_points_homo = np.hstack([world_points, ones])
        else:
            world_points_homo = world_points
        
        # Apply inverse homography transformation
        pixel_points_homo = inv_homography @ world_points_homo.T
        
        # Convert back to 2D coordinates
        pixel_points = (pixel_points_homo[:2] / pixel_points_homo[2]).T
        
        return pixel_points
    
    def save_calibration(self, filename: str = "camera_calibration.json"):
        """Save calibration parameters to file"""
        calibration_data = {
            "homography_matrix": self.homography_matrix.tolist() if self.homography_matrix is not None else None,
            "image_corners": self.image_corners.tolist() if self.image_corners is not None else None,
            "real_world_corners": self.real_world_corners.tolist() if self.real_world_corners is not None else None
        }
        
        with open(filename, 'w') as f:
            json.dump(calibration_data, f, indent=2)
    
    def load_calibration(self, filename: str = "camera_calibration.json") -> bool:
        """Load calibration parameters from file"""
        # Try to load the new enhanced calibration first
        if os.path.exists("camera_calibration_data.json"):
            try:
                with open("camera_calibration_data.json", 'r') as f:
                    calibration_data = json.load(f)
                
                if calibration_data["homography_matrix"] is not None:
                    self.homography_matrix = np.array(calibration_data["homography_matrix"])
                if calibration_data.get("image_corners") is not None:
                    self.image_corners = np.array(calibration_data["image_corners"])
                if calibration_data.get("real_world_corners") is not None:
                    self.real_world_corners = np.array(calibration_data["real_world_corners"])
                
                print("✅ Loaded enhanced coordinate calibration")
                return True
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️  Failed to load enhanced calibration: {e}")
        
        # Fallback to original calibration file
        try:
            with open(filename, 'r') as f:
                calibration_data = json.load(f)
            
            if calibration_data["homography_matrix"] is not None:
                self.homography_matrix = np.array(calibration_data["homography_matrix"])
            if calibration_data.get("image_corners") is not None:
                self.image_corners = np.array(calibration_data["image_corners"])
            if calibration_data.get("real_world_corners") is not None:
                self.real_world_corners = np.array(calibration_data["real_world_corners"])
            
            print("✅ Loaded original calibration")
            return True
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            print("❌ No calibration file found")
            return False

class ShopperCoordinateTracker:
    def __init__(self, calibrator: CameraCalibrator):
        self.calibrator = calibrator
        self.tracked_coordinates = []
    
    def add_shopper_detection(self, pixel_x: int, pixel_y: int, timestamp: str, shopper_id: str = None):
        """
        Add a shopper detection with pixel coordinates and convert to world coordinates
        """
        pixel_point = np.array([[pixel_x, pixel_y]], dtype=np.float32)
        world_point = self.calibrator.pixel_to_world_coordinates(pixel_point)[0]
        
        detection = {
            "timestamp": timestamp,
            "shopper_id": shopper_id,
            "pixel_coordinates": {"x": int(pixel_x), "y": int(pixel_y)},
            "world_coordinates": {"x": float(world_point[0]), "y": float(world_point[1])}
        }
        
        self.tracked_coordinates.append(detection)
    
    def export_to_json(self, filename: str = "shopper_coordinates.json"):
        """Export all tracked coordinates to JSON file"""
        export_data = {
            "calibration_info": {
                "coordinate_system": "Real-world coordinates in units as defined in calibration",
                "origin": "Bottom-left corner of the tracked area"
            },
            "detections": self.tracked_coordinates
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filename
    
    def clear_tracking_data(self):
        """Clear all tracked coordinate data"""
        self.tracked_coordinates = []

def main():
    """Main function to demonstrate calibration process"""
    calibrator = CameraCalibrator()
    
    # Try to load existing calibration
    if calibrator.load_calibration():
        print("Loaded existing calibration")
    else:
        # Perform new calibration
        print("Performing camera calibration...")
        
        # Use the layout grid image for calibration
        layout_image = os.path.join(calibrator.calib_images_dir, "3d_layout_grid_xy.png")
        
        if os.path.exists(layout_image):
            if calibrator.calibrate_with_homography(layout_image):
                print("Calibration successful!")
                calibrator.save_calibration()
            else:
                print("Calibration failed!")
                return
        else:
            print(f"Layout image not found: {layout_image}")
            return
    
    # Create coordinate tracker
    tracker = ShopperCoordinateTracker(calibrator)
    
    # Example usage: add some sample detections
    import datetime
    current_time = datetime.datetime.now().isoformat()
    
    # Add sample shopper detections (you would get these from your detection system)
    tracker.add_shopper_detection(320, 240, current_time, "shopper_001")
    tracker.add_shopper_detection(450, 180, current_time, "shopper_002")
    
    # Export coordinates to JSON
    output_file = tracker.export_to_json()
    print(f"Coordinates exported to: {output_file}")

if __name__ == "__main__":
    main()