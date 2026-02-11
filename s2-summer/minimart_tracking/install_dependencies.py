#!/usr/bin/env python3
"""
Minimart YOLOv8s Tracking System - Dependency Installer
======================================================

This script automatically installs all necessary dependencies and sets up
the environment for the YOLOv8s person tracking system with HAILO8L acceleration.

Usage:
    python install_dependencies.py

Requirements:
    - Raspberry Pi 5 with HAILO8L AI accelerator
    - Python 3.11+
    - Sudo privileges for system packages
"""

import subprocess
import sys
import os
import platform
import json
from pathlib import Path

class DependencyInstaller:
    def __init__(self):
        self.python_packages = [
            # Core AI/ML packages
            "ultralytics>=8.0.0",
            "opencv-python>=4.8.0",
            "numpy>=1.24.0",
            
            # Web framework
            "flask>=2.3.0",
            "flask-socketio>=5.3.0",
            
            # Tracking and processing
            "scipy>=1.10.0",
            "scikit-learn>=1.3.0",
            "filterpy>=1.4.5",
            
            # Data handling
            "pandas>=2.0.0",
            "openpyxl>=3.1.0",
            
            # Camera support
            "picamera2",
            
            # HAILO support (if available)
            "hailo-platform",
        ]
        
        self.system_packages = [
            # HAILO8L support
            "hailo-all",
            
            # Camera and media
            "libcamera-apps",
            "python3-picamera2",
            
            # Development tools
            "python3-dev",
            "python3-pip",
            "python3-venv",
            
            # System libraries
            "libopencv-dev",
            "libatlas-base-dev",
            "libjpeg-dev",
            "libpng-dev",
            "libwebp-dev",
            
            # Build tools
            "build-essential",
            "cmake",
            "pkg-config",
        ]
        
        self.optional_packages = [
            # Performance monitoring
            "htop",
            "iotop",
            "stress-ng",
            
            # Development utilities
            "git",
            "curl",
            "wget",
            "nano",
        ]
    
    def print_header(self, title):
        """Print a formatted header"""
        print("\n" + "="*60)
        print(f"  {title}")
        print("="*60)
    
    def print_step(self, step_num, total_steps, description):
        """Print a formatted step"""
        print(f"\n[{step_num}/{total_steps}] {description}")
        print("-" * 40)
    
    def run_command(self, command, description="", check=True):
        """Run a shell command with error handling"""
        print(f"Running: {command}")
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                check=check, 
                capture_output=True, 
                text=True
            )
            if result.stdout:
                print(f"✅ Output: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Error: {e}")
            if e.stderr:
                print(f"Error details: {e.stderr.strip()}")
            return False
    
    def check_system_requirements(self):
        """Check if system meets requirements"""
        self.print_step(1, 8, "Checking System Requirements")
        
        # Check Python version
        python_version = sys.version_info
        print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        if python_version < (3, 11):
            print("❌ Python 3.11+ required")
            return False
        else:
            print("✅ Python version OK")
        
        # Check platform
        system = platform.system()
        machine = platform.machine()
        print(f"Platform: {system} {machine}")
        
        if system != "Linux" or machine not in ["aarch64", "armv7l"]:
            print("⚠️  This installer is optimized for Raspberry Pi (ARM Linux)")
            print("   Some packages may not be available for your platform")
        else:
            print("✅ Platform compatible")
        
        # Check if running as root (not recommended)
        if os.geteuid() == 0:
            print("⚠️  Running as root is not recommended")
            print("   Please run as regular user with sudo privileges")
        
        return True
    
    def update_system(self):
        """Update system package lists"""
        self.print_step(2, 8, "Updating System Package Lists")
        
        commands = [
            "sudo apt update",
            "sudo apt upgrade -y"
        ]
        
        for cmd in commands:
            if not self.run_command(cmd, check=False):
                print("⚠️  System update had issues, continuing anyway...")
    
    def install_system_packages(self):
        """Install system packages"""
        self.print_step(3, 8, "Installing System Packages")
        
        # Install packages one by one to handle failures gracefully
        for package in self.system_packages:
            print(f"Installing {package}...")
            success = self.run_command(
                f"sudo apt install -y {package}", 
                check=False
            )
            if success:
                print(f"✅ {package} installed successfully")
            else:
                print(f"⚠️  {package} installation failed, continuing...")
    
    def create_virtual_environment(self):
        """Create Python virtual environment"""
        self.print_step(4, 8, "Creating Virtual Environment")
        
        venv_path = "venv_tracking"
        
        if os.path.exists(venv_path):
            print(f"Virtual environment {venv_path} already exists")
            return venv_path
        
        if self.run_command(f"python3 -m venv {venv_path}"):
            print(f"✅ Virtual environment created: {venv_path}")
            return venv_path
        else:
            print("❌ Failed to create virtual environment")
            return None
    
    def install_python_packages(self, venv_path=None):
        """Install Python packages"""
        self.print_step(5, 8, "Installing Python Packages")
        
        # Determine pip command
        if venv_path:
            pip_cmd = f"{venv_path}/bin/pip"
        else:
            pip_cmd = "pip3"
        
        # Upgrade pip first
        self.run_command(f"{pip_cmd} install --upgrade pip", check=False)
        
        # Install packages one by one
        failed_packages = []
        for package in self.python_packages:
            print(f"Installing {package}...")
            success = self.run_command(
                f"{pip_cmd} install '{package}'", 
                check=False
            )
            if success:
                print(f"✅ {package} installed successfully")
            else:
                print(f"⚠️  {package} installation failed")
                failed_packages.append(package)
        
        if failed_packages:
            print(f"\n⚠️  Failed packages: {', '.join(failed_packages)}")
            print("These packages may not be available for your platform")
    
    def setup_hailo_environment(self):
        """Setup HAILO8L specific environment"""
        self.print_step(6, 8, "Setting up HAILO8L Environment")
        
        # Check if HAILO device is available
        hailo_check = self.run_command("lspci | grep -i hailo", check=False)
        if hailo_check:
            print("✅ HAILO device detected")
        else:
            print("⚠️  HAILO device not detected - ensure HAILO8L is properly connected")
        
        # Check HailoRT service
        service_check = self.run_command("systemctl is-active hailort", check=False)
        if service_check:
            print("✅ HailoRT service is active")
        else:
            print("⚠️  HailoRT service not active - may need manual configuration")
        
        # Set environment variables for HAILO
        env_setup = """
# HAILO Environment Variables (add to ~/.bashrc if needed)
export HAILO_MODEL_ZOO_PATH=/usr/share/hailo-models
export HAILO_EXAMPLES_PATH=/usr/share/hailo-examples
"""
        print("Environment setup suggestions:")
        print(env_setup)
    
    def create_requirements_file(self):
        """Create requirements.txt file"""
        self.print_step(7, 8, "Creating Requirements File")
        
        requirements_content = """# YOLOv8s Tracking System - Python Dependencies
# Core AI/ML packages
ultralytics>=8.0.0
opencv-python>=4.8.0
numpy>=1.24.0

# Web framework
flask>=2.3.0
flask-socketio>=5.3.0

# Tracking and processing
scipy>=1.10.0
scikit-learn>=1.3.0
filterpy>=1.4.5

# Data handling
pandas>=2.0.0
openpyxl>=3.1.0

# Camera support (Raspberry Pi)
picamera2

# HAILO support (if available)
# hailo-platform

# Optional performance packages
# psutil>=5.9.0
# memory-profiler>=0.60.0
"""
        
        with open("requirements.txt", "w") as f:
            f.write(requirements_content)
        
        print("✅ requirements.txt created")
        print("   You can install these later with: pip install -r requirements.txt")
    
    def verify_installation(self):
        """Verify the installation"""
        self.print_step(8, 8, "Verifying Installation")
        
        verification_script = """
import sys
print(f"Python: {sys.version}")

# Test core packages
try:
    import cv2
    print(f"✅ OpenCV: {cv2.__version__}")
except ImportError:
    print("❌ OpenCV not available")

try:
    import numpy as np
    print(f"✅ NumPy: {np.__version__}")
except ImportError:
    print("❌ NumPy not available")

try:
    import ultralytics
    print("✅ Ultralytics YOLO available")
except ImportError:
    print("❌ Ultralytics not available")

try:
    from flask import Flask
    print("✅ Flask available")
except ImportError:
    print("❌ Flask not available")

try:
    import picamera2
    print("✅ Picamera2 available")
except ImportError:
    print("❌ Picamera2 not available")

try:
    import hailo_platform
    print("✅ HAILO platform available")
except ImportError:
    print("⚠️  HAILO platform not available (may need manual installation)")
"""
        
        # Write verification script
        with open("verify_installation.py", "w") as f:
            f.write(verification_script)
        
        print("Running verification...")
        self.run_command("python3 verify_installation.py", check=False)
    
    def print_completion_message(self):
        """Print completion message with next steps"""
        self.print_header("Installation Complete!")
        
        next_steps = """
🎉 Installation completed successfully!

Next Steps:
1. Activate virtual environment (if created):
   source venv_tracking/bin/activate

2. Test the tracking system:
   python yolov8s_tracking_with_coordinates.py

3. Access the web interface:
   http://localhost:5000

4. For HAILO8L models, ensure you have the model files:
   - models/yolo_v8_crowdhuman--640x640_quant_hailort_multidevice_1/
   - models/custom_yolo_deployment/

Troubleshooting:
- Check system logs: journalctl -u hailort
- Verify HAILO device: lspci | grep -i hailo
- Test camera: libcamera-hello
- Check Python packages: python -c "import cv2, numpy, ultralytics"

Documentation: See DEVELOPMENT_SUMMARY.md for detailed information.
"""
        print(next_steps)
    
    def run_installation(self):
        """Run the complete installation process"""
        self.print_header("YOLOv8s Tracking System - Dependency Installer")
        
        print("This installer will set up all dependencies for the YOLOv8s tracking system")
        print("with HAILO8L hardware acceleration support.")
        print("\nPress Ctrl+C to cancel at any time.")
        
        try:
            input("\nPress Enter to continue...")
        except KeyboardInterrupt:
            print("\n❌ Installation cancelled by user")
            return False
        
        try:
            # Run installation steps
            if not self.check_system_requirements():
                return False
            
            self.update_system()
            self.install_system_packages()
            
            venv_path = self.create_virtual_environment()
            self.install_python_packages(venv_path)
            
            self.setup_hailo_environment()
            self.create_requirements_file()
            self.verify_installation()
            
            self.print_completion_message()
            return True
            
        except KeyboardInterrupt:
            print("\n❌ Installation cancelled by user")
            return False
        except Exception as e:
            print(f"\n❌ Installation failed with error: {e}")
            return False

def main():
    """Main installation function"""
    installer = DependencyInstaller()
    success = installer.run_installation()
    
    if success:
        print("\n🎉 Installation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Installation failed or was cancelled")
        sys.exit(1)

if __name__ == "__main__":
    main()