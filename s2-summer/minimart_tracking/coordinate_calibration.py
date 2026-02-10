#!/usr/bin/env python3
"""
Enhanced Camera Coordinate Calibration using labeled coordinate images
Uses images with checkerboards at known coordinates (0x0y, 0x100y, 100x100y)
"""

import cv2
import numpy as np
import json
import os
from typing import List, Tuple, Optional, Dict
import glob

class CoordinateCalibrator:
    def __init__(self, opencv_img_dir: str = "opencv_img"):
        self.opencv_img_dir = opencv_img_dir
        self.homography_matrix = None
        self.coordinate_points = {}  # Store image points and world coordinates
        
        # Checkerboard parameters
        self.checkerboard_size = (9, 6)  # Inner corners (adjust if different)
        self.square_size = 1.0  # Size of each square in world units
        
    def detect_checkerboard_center(self, image_path: str) -> Optional[Tuple[float, float]]:
        """
        Detect the center of the checkerboard in the image
        """
        image = cv2.imread(image_path)
        if image is None:
            print(f"Could not load image: {image_path}")
            return None
            
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Find checkerboard corners
        ret, corners = cv2.findChessboardCorners(gray, self.checkerboard_size, None)
        
        if ret:
            # Refine corner positions
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            
            # Calculate center of checkerboard
            center_x = np.mean(corners[:, 0, 0])
            center_y = np.mean(corners[:, 0, 1])
            
            return (center_x, center_y)
        else:
            print(f"Could not find checkerboard in {image_path}")
            # Fallback: try to detect checkerboard using template matching or manual detection
            return self.detect_checkerboard_fallback(gray)
    
    def detect_checkerboard_fallback(self, gray_image: np.ndarray) -> Optional[Tuple[float, float]]:
        """
        Fallback method to detect checkerboard center using contour detection
        """
        # Apply threshold to get binary image
        _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Find the largest rectangular contour (likely the checkerboard)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Calculate center
            center_x = x + w / 2
            center_y = y + h / 2
            
            return (center_x, center_y)
        
        return None
    
    def parse_coordinate_from_filename(self, filename: str) -> Optional[Tuple[float, float]]:
        """
        Parse world coordinates from filename (e.g., '0x100y.jpg' -> (0, 100))
        """
        base_name = os.path.basename(filename).lower()
        
        # Parse different filename formats
        if '0x0y' in base_name:
            return (0.0, 0.0)
        elif '0x100y' in base_name:
            return (0.0, 100.0)
        elif '100x100y' in base_name:
            return (100.0, 100.0)
        elif '100x0y' in base_name:
            return (100.0, 0.0)
        
        return None
    
    def manual_calibration_points(self):
        """
        Manually define calibration points based on visual inspection of the images
        """
        # Based on the checkerboard positions visible in the images
        # Coordinates estimated from the checkerboard centers
        manual_points = {
            '0x0y.jpg': {
                'image_point': (567.0, 928.0),  # Checkerboard center in bottom left area (0,0 in world)
                'world_point': (0.0, 0.0)
            },
            '0x100y.jpg': {
                'image_point': (567.0, 400.0),  # Checkerboard center in top left area (0,100 in world) 
                'world_point': (0.0, 100.0)
            },
            '100x100y.jpg': {
                'image_point': (1200.0, 400.0),  # Checkerboard center in top right area (100,100 in world)
                'world_point': (100.0, 100.0)
            },
            # Add a 4th point for better homography - extrapolated bottom right
            'extrapolated': {
                'image_point': (1200.0, 928.0),  # Bottom right corner (100,0 in world)
                'world_point': (100.0, 0.0)
            }
        }
        return manual_points

    def collect_calibration_points(self) -> bool:
        """
        Collect image points and corresponding world coordinates from labeled images
        """
        coordinate_images = [
            '0x0y.jpg',
            '0x100y.jpg', 
            '100x100y.jpg'
        ]
        
        self.coordinate_points = {}
        
        for image_name in coordinate_images:
            image_path = os.path.join(self.opencv_img_dir, image_name)
            
            if not os.path.exists(image_path):
                print(f"Warning: {image_path} not found")
                continue
            
            # Get world coordinates from filename
            world_coords = self.parse_coordinate_from_filename(image_name)
            if world_coords is None:
                print(f"Could not parse coordinates from {image_name}")
                continue
            
            # Detect checkerboard center in image
            image_center = self.detect_checkerboard_center(image_path)
            if image_center is None:
                print(f"Could not detect checkerboard in {image_name}")
                continue
            
            self.coordinate_points[image_name] = {
                'image_point': image_center,
                'world_point': world_coords
            }
            
            print(f"✅ {image_name}: Image({image_center[0]:.1f}, {image_center[1]:.1f}) -> World{world_coords}")
        
        # If we don't have enough good points or coordinates are wrong, use manual calibration
        if len(self.coordinate_points) < 4:
            print("⚠️  Using manual calibration points")
            self.coordinate_points = self.manual_calibration_points()
            
            for name, data in self.coordinate_points.items():
                print(f"📍 {name}: Image({data['image_point'][0]:.1f}, {data['image_point'][1]:.1f}) -> World{data['world_point']}")
        
        return len(self.coordinate_points) >= 4
    
    def calculate_homography(self) -> bool:
        """
        Calculate homography matrix from collected points
        """
        if len(self.coordinate_points) < 3:
            print("Need at least 3 coordinate points for calibration")
            return False
        
        # Prepare points for homography calculation
        image_points = []
        world_points = []
        
        for data in self.coordinate_points.values():
            image_points.append(data['image_point'])
            world_points.append(data['world_point'])
        
        image_points = np.array(image_points, dtype=np.float32)
        world_points = np.array(world_points, dtype=np.float32)
        
        # Calculate homography matrix
        self.homography_matrix, mask = cv2.findHomography(
            image_points, world_points, 
            cv2.RANSAC, 5.0
        )
        
        if self.homography_matrix is not None:
            print("✅ Homography matrix calculated successfully")
            print("Homography matrix:")
            print(self.homography_matrix)
            return True
        else:
            print("❌ Failed to calculate homography matrix")
            return False
    
    def test_calibration(self) -> None:
        """
        Test the calibration by converting back the known points
        """
        if self.homography_matrix is None:
            print("No calibration available to test")
            return
        
        print("\n📊 Testing calibration accuracy:")
        print("Image Point -> Expected World -> Calculated World -> Error")
        
        total_error = 0
        count = 0
        
        for image_name, data in self.coordinate_points.items():
            image_point = np.array([data['image_point']], dtype=np.float32)
            expected_world = data['world_point']
            
            # Convert using homography
            calculated_world = cv2.perspectiveTransform(
                image_point.reshape(1, 1, 2), 
                self.homography_matrix
            ).reshape(2)
            
            # Calculate error
            error = np.sqrt((calculated_world[0] - expected_world[0])**2 + 
                          (calculated_world[1] - expected_world[1])**2)
            
            total_error += error
            count += 1
            
            print(f"{image_name}: ({image_point[0][0]:.1f},{image_point[0][1]:.1f}) -> "
                  f"{expected_world} -> ({calculated_world[0]:.1f},{calculated_world[1]:.1f}) "
                  f"Error: {error:.2f}")
        
        avg_error = total_error / count if count > 0 else 0
        print(f"\n📈 Average calibration error: {avg_error:.2f} units")
    
    def pixel_to_world_coordinates(self, pixel_points: np.ndarray) -> np.ndarray:
        """
        Convert pixel coordinates to world coordinates using homography
        """
        if self.homography_matrix is None:
            raise ValueError("Camera not calibrated. Run calibration first.")
        
        # Ensure points are in correct format
        if pixel_points.ndim == 1:
            pixel_points = pixel_points.reshape(1, -1)
        
        # Convert using homography
        world_points = cv2.perspectiveTransform(
            pixel_points.reshape(-1, 1, 2).astype(np.float32),
            self.homography_matrix
        ).reshape(-1, 2)
        
        return world_points
    
    def save_calibration(self, filename: str = "coordinate_calibration.json") -> None:
        """
        Save calibration data to JSON file
        """
        if self.homography_matrix is None:
            print("No calibration data to save")
            return
        
        calibration_data = {
            'homography_matrix': self.homography_matrix.tolist(),
            'coordinate_points': {
                name: {
                    'image_point': data['image_point'],
                    'world_point': data['world_point']
                }
                for name, data in self.coordinate_points.items()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(calibration_data, f, indent=2)
        
        print(f"✅ Calibration saved to {filename}")
    
    def load_calibration(self, filename: str = "coordinate_calibration.json") -> bool:
        """
        Load calibration data from JSON file
        """
        try:
            with open(filename, 'r') as f:
                calibration_data = json.load(f)
            
            self.homography_matrix = np.array(calibration_data['homography_matrix'])
            self.coordinate_points = calibration_data['coordinate_points']
            
            print(f"✅ Calibration loaded from {filename}")
            return True
        except Exception as e:
            print(f"❌ Could not load calibration: {e}")
            return False

def run_coordinate_calibration():
    """
    Main function to run the coordinate calibration process
    """
    print("🎯 Starting Enhanced Coordinate Calibration")
    
    calibrator = CoordinateCalibrator()
    
    # Check if images exist
    if not os.path.exists(calibrator.opencv_img_dir):
        print(f"❌ Image directory {calibrator.opencv_img_dir} not found")
        return False
    
    # Collect calibration points
    print("\n📸 Collecting calibration points...")
    if not calibrator.collect_calibration_points():
        print("❌ Failed to collect enough calibration points")
        return False
    
    # Calculate homography
    print("\n🔢 Calculating homography matrix...")
    if not calibrator.calculate_homography():
        print("❌ Failed to calculate homography")
        return False
    
    # Test calibration
    calibrator.test_calibration()
    
    # Save calibration
    print("\n💾 Saving calibration...")
    calibrator.save_calibration()
    
    # Also save in camera_calibration format for compatibility
    save_compatible_calibration(calibrator)
    
    print("\n✅ Coordinate calibration completed successfully!")
    return True

def save_compatible_calibration(calibrator: CoordinateCalibrator):
    """
    Save calibration in format compatible with existing camera_calibration.py
    """
    calibration_data = {
        'homography_matrix': calibrator.homography_matrix.tolist(),
        'image_corners': [list(data['image_point']) for data in calibrator.coordinate_points.values()],
        'real_world_corners': [list(data['world_point']) for data in calibrator.coordinate_points.values()]
    }
    
    with open('camera_calibration_data.json', 'w') as f:
        json.dump(calibration_data, f, indent=2)
    
    print("✅ Compatible calibration saved to camera_calibration_data.json")

if __name__ == "__main__":
    run_coordinate_calibration()