#!/usr/bin/env python3
"""
Quick Setup Script for YOLOv8s Tracking System
=============================================

A simplified installer for essential dependencies only.
Use this for faster setup on systems where most dependencies are already available.

Usage:
    python quick_setup.py
"""

import subprocess
import sys
import os

def run_cmd(cmd, description=""):
    """Run command with basic error handling"""
    print(f"🔄 {description}")
    print(f"   Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"   ✅ Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed: {e}")
        return False

def quick_install():
    """Quick installation of essential packages"""
    print("🚀 YOLOv8s Tracking - Quick Setup")
    print("=" * 40)
    
    # Essential Python packages
    essential_packages = [
        "ultralytics",
        "opencv-python", 
        "flask",
        "flask-socketio",
        "numpy",
        "scipy"
    ]
    
    # Update pip
    run_cmd("python3 -m pip install --upgrade pip", "Upgrading pip")
    
    # Install essential packages
    for package in essential_packages:
        run_cmd(f"python3 -m pip install {package}", f"Installing {package}")
    
    # Try to install camera support
    run_cmd("python3 -m pip install picamera2", "Installing camera support")
    
    # Create basic requirements file
    requirements = """ultralytics>=8.0.0
opencv-python>=4.8.0
flask>=2.3.0
flask-socketio>=5.3.0
numpy>=1.24.0
scipy>=1.10.0
picamera2
"""
    
    with open("requirements_minimal.txt", "w") as f:
        f.write(requirements)
    
    print("\n✅ Quick setup complete!")
    print("📄 Created requirements_minimal.txt")
    print("\n🚀 Try running: python yolov8s_tracking_with_coordinates.py")

if __name__ == "__main__":
    quick_install()