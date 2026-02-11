# 🛒 Minimart: Edge AI Retail Analytics

**Minimart** is a production-ready edge computing solution for real-time retail analytics. It leverages the **Raspberry Pi 5** for orchestration and the **Hailo-8L NPU** for high-performance, low-latency computer vision.

The system tracks customer movements, analyses dwell times, generates heatmaps, and provides a context-aware "Chat with your Store" AI assistant— processed locally on the edge.

---

## System Architecture

The system follows a **Headless API** pattern to decouple high-speed inference from the modern user interface.

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
    
- **Raspberry Pi Camera Module**

---

## Installation & Setup

### 1. Prerequisites

Ensure your Pi 5 has the Hailo drivers and Node.js installed.

### 2. Backend Setup 

Bash

```
cd ~/minimart

# Create Virtual Environment (System packages enabled for Hailo compatibility)
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

Bash

```
cd ~/minimart/dashboard

# Install Node Modules
npm install
```

---

## Integration Configuration (AI Keys)

To enable the "Ask Your Store" Chatbot features, you must configure your API keys. The system supports both `OpenAI` and `AWS Bedrock`.

1. Navigate to the dashboard directory:
    
    
    ```
    cd ~/minimart/dashboard
    ```
    
2. Create a local environment file:

    ```
    cp .env.example .env.local
    ```
    

**Example `.env.local` configuration:**


```TOML
# --- AI Provider Configuration ---
# Options: 'openai' or 'bedrock'
AI_PROVIDER=openai

# If using OpenAI (or Local LLM like Ollama)
OPENAI_API_KEY=sk-your-key-here
# OPENAI_BASE_URL=http://localhost:11434/v1  <-- Uncomment for Local LLM

# If using AWS Bedrock
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
```

---

## How to Run

You need two terminal windows (or a multiplexer like `tmux`) to run the full stack.

### Terminal 1: API & AI

This starts the Camera, `Hailo` Detector, and Flask Server.



```
cd ~/minimart
./run.sh
```


### Terminal 2: Dashboard

This starts the Next.js User Interface.


```
cd ~/minimart/dashboard
npm run dev
```

- **Access the Dashboard:** Open your browser to `http://localhost:3000` (or your Pi's IP address: `http://<PI_IP>:3000`).
    
- **Login Credentials (Local):**
    
    - **Email:** `admin@minimart.com`
        
    - **Password:** `password123`
        

---

## 🌟Features

### 1. Live Computer Vision Feed

- Real-time video stream embedded directly in the dashboard.
    
- **Hardware Accelerated:** Uses `rpicam-vid` pipe to bypass GStreamer overhead.
    
- **Visuals:** Bounding boxes and FPS overlays are burned into the stream for easy debugging.
    

### 2. Intelligent Tracking & Analytics

- **Multi-Object Tracking (MOT):** Assigns persistent IDs to shoppers using spatial logic.
    
- **Zone Analytics:** Detects which "Aisle" or "Zone" a shopper is currently in.
    
- **Dwell Time:** Calculates how long customers stay in specific areas.
    

### 3. "Ask Your Store" AI Assistant

- Integrated Chatbot powered by OpenAI or AWS Bedrock.
    
- **Context Aware:** The bot has access to real-time stats (e.g., _"How many people are in the store right now?"_).
    

---

## 📂 Project Structure

Plaintext

```
minimart/
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
│   ├── .env.local           # API Keys (GitIgnored)
│   └── public/              # Static Assets
├── crowdhuman_hailo_detector.py  # Custom Hailo Inference Engine
├── main.py                  # Flask API Entry Point
├── run.sh                   # Startup Script (handles venv & hardware init)
└── README.md                # This file
```