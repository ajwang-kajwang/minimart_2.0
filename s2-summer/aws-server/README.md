# Minimart IoT Sensor and Camera Data Pipeline
### by **Brian Ngo**  
📧 ngbao128@gmail.com

This program connects to **AWS IoT Core**, subscribes to an MQTT topic, receives IoT sensor messages, and processes them for storage in both **Amazon S3** and **PostgreSQL**.

---

## 🚀 Features
- Connects securely to AWS IoT Core using device certificates
- Subscribes to MQTT topic (`minimart/wa/bentley/sensor/1`)
- Processes sensor data (temperature, pressure, humidity)
- Saves raw messages as JSON files in S3 with timestamps
- Stores structured sensor data in PostgreSQL (powerbi_data schema)
- Modular architecture with separate sensor handling module

---

## 📦 Requirements

1. **Python 3.8+**

2. Virtual environment
- Create virtual environment
   ```bash
   python -m venv venv
   ```
- Activate virtual environment
   ```bash
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install Docker
   ```bash
   sudo apt-get update
   ```
   ```bash
   sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```
   ```bash
   sudo systemctl start docker
   ```
   ```bash
   sudo systemctl enable docker
   ```

5. Copy Certificate to certs folder
   ```bash
   mkdir camera
   mkdir sensor
   ```

---
## How to run
2. Copy .env file
   ```bash
   cp .env.example .env
   cp postgres/.env.example postgres/.env 
   ```
2. Start the database:
   ```bash
   docker-compose -f postgres/docker-compose.yml up -d
   ```
3. Stop the database:
   ```bash
   docker-compose -f postgres/docker-compose.yml down
   ```
4. Connect to database:
   ```bash
   docker-compose -f postgres/docker-compose.yml exec postgres psql -U minimart_user -d minimart_db
   ```
5. Run main file:
   ```bash
   python3 src/main.py
   ```

---

## 📁 Project Structure

```
minimart/
├── src/
│   ├── main.py          # Entry point - simple IoT client launcher
│   └── sensor.py        # SensorDataHandler class with IoT & data processing
├── postgres/
│   ├── docker-compose.yml
│   └── init.sh          # Database schema initialization
├── certs/               # AWS IoT device certificates
├── requirements.txt
├── .env.example
└── README.md
```

## 🗄️ Database Schema

The PostgreSQL database contains:

### `powerbi_data.sensor_data`
- Stores structured sensor readings
- Columns: `id`, `thing`, `temperature_c`, `pressure_hpa`, `humidity_rh`, `time`

### `powerbi_data.zone_dim` 
- Zone definitions for minimart layout
- Used for spatial analysis and heatmap generation

### `powerbi_data.camera_data`
- Customer tracking data from cameras
- Links to zones for movement analysis

### Views
- `powerbi_data.heatmap_view` - Generates coordinate grid with people counts for visualization