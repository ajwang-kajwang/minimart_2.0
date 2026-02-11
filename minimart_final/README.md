
# Minimart 2.0: AI Retail Analytics
**Minimart 2.0** is an edge-computing solution for real-time retail analytics. It runs on the **Raspberry Pi 5** with the **Hailo-8L** NPU for high-performance, low-latency computer vision.

The system tracks customer movements, analyses dwell times, generates heatmaps, and provides a "Chat with your Store" AI assistant—processed locally on the edge.

---

## System Architecture

The system follows a **Headless API** pattern to decouple high-speed inference from the modern UI.

|**Component**|**Tech Stack**|**Port**|**Role**|
|---|---|---|---|
|**Backend**|Python 3.11, Flask, Socket.IO|`:5000`|Hardware control, AI Inference (Hailo), Tracking Logic, API Server.|
|**Frontend**|Next.js 14, React, Tailwind, Recharts|`:3000`|Interactive Dashboard, Real-time Charts, Live Video Stream.|
|**AI Engine**|YOLOv8 (Hailo-8L HEF), CrowdHuman|N/A|Person detection running at ~30 FPS on the Hailo-8L NPU.|
|**Camera**|`rpicam-vid` (Native), OpenCV|N/A|Zero-copy video capture pipeline via raw YUV stream.|

---

## Hardware Requirements

- **Raspberry Pi 5** (4GB or 8GB recommended).
    
- **Hailo-8L AI Kit** (M.2 HAT + Hailo-8L Module).
    
- **Raspberry Pi Camera Module 

---

## Installation & Setup


```
cd ~/minimart_2.0

# Create Virtual Environment (System packages enabled for Hailo compatibility)
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt
```

---

## How to Run

You need two terminal windows to run the full stack.
### Terminal 1: The Backend 

This starts the Camera, Hailo Detector, and Flask Server.

Bash

```
cd ~/minimart_2.0
./run.sh
```
### Terminal 2: The Frontend (Dashboard)

This starts the Next.js User Interface.

Bash

```
cd ~/minimart_2.0/dashboard
npm run dev
```

- **Access the Dashboard:** Open your browser to `http://localhost:3000` (or your Pi's IP address: `http://<PI_IP>:3000`).

---

## Key Features

### 1. Live Computer Vision Feed

- Real-time video stream embedded directly in the dashboard.
    
- **Hardware Accelerated:** Uses `rpicam-vid` pipe to bypass GStreamer overhead.
    
- **Visuals:** Bounding boxes and FPS overlays are burned into the stream for easy debugging.
    

### 2. Tracking & Analytics

- **Multi-Object Tracking (MOT):** Assigns persistent IDs to shoppers using spatial logic.
    
- **Zone Analytics:** Detects which "Aisle" or "Zone" a shopper is currently in.
    
- **Dwell Time:** Calculates how long customers stay in specific areas.
    

### 3. "Ask Your Store" AI Assistant

- Integrated Chatbot powered by OpenAI (via Proxy) or AWS Bedrock.
    
- **Context Aware:** The bot has access to real-time stats (e.g., _"How many people are in the store right now?"_).
    

---

## Project Structure


```
minimart_2.0/
├── models/                  # Compiled HEF models for Hailo-8L
├── infrastructure/          # Hardware abstraction layers
│   └── camera.py            # Native rpicam-vid interface
├── services/                # Core Business Logic
│   ├── detection.py         # YOLO Inference Manager
│   ├── tracking.py          # ID & Trajectory Tracking
│   └── analytics.py         # Zone & Dwell Time Logic
├── dashboard/               # Next.js Frontend Application
│   ├── src/app/             # Pages & Routing
│   ├── src/components/      # UI Widgets (LiveStream, Charts)
│   └── public/              # Static Assets
├── crowdhuman_hailo_detector.py  # Custom Hailo Inference Engine
├── main.py                  # Flask API Entry Point
├── run.sh                   # Startup Script (handles venv & hardware init)
└── README.md                
```

---

