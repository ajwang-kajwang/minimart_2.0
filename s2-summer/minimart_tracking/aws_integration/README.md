# AWS IoT Integration

This directory contains AWS IoT Core integration scripts for the YOLOv8s tracking system.

## Files

### `send_sensor_to_aws.py`
- **Purpose**: Sends sensor data (BME280) to AWS IoT Core
- **Features**: 
  - Temperature, pressure, humidity readings
  - MQTT publish with mTLS authentication
  - JSON data format for AWS ingestion
- **Topic**: `minimart/wa/bentley/sensor/1`

### `start.sh`
- **Purpose**: Setup and run AWS IoT device SDK
- **Features**:
  - Downloads AWS Root CA certificate
  - Installs AWS IoT Device SDK
  - Runs pub/sub sample application
- **Endpoint**: `a1ajomln5m8rkh-ats.iot.ap-southeast-2.amazonaws.com`

## Prerequisites

### Required Certificates (Not in Repository)
```
minimart-wa-bentley-sensor-1.cert.pem     # Device certificate
minimart-wa-bentley-sensor-1.private.key  # Private key
root-CA.crt                               # AWS Root CA
```

### Dependencies
```bash
pip install awsiotsdk awscrt
```

### Hardware
- Raspberry Pi 5
- PiicoDev BME280 sensor (for sensor script)

## Usage

### Setup AWS IoT
```bash
# Make script executable
chmod +x start.sh

# Run setup and test
./start.sh
```

### Send Sensor Data
```bash
# Ensure certificates are in place
python3 send_sensor_to_aws.py
```

## Integration with Tracking System

To integrate with the YOLOv8s tracking system:

1. **Coordinate Data**: Modify `send_sensor_to_aws.py` to send tracking coordinates
2. **Topic Structure**: Use `minimart/wa/bentley/shopper/coordinates`
3. **Data Format**: 
```json
{
  "timestamp": "2025-11-02T22:45:00.000Z",
  "shoppers": [
    {"id": "1", "loc": "45.2,67.8"},
    {"id": "2", "loc": "23.1,89.4"}
  ]
}
```

## Security Notes

- Certificates and private keys are **NOT** included in this repository
- Store certificates securely outside version control
- Use AWS IAM policies to restrict device permissions
- Endpoint and topics are specific to the minimart deployment

## AWS IoT Core Configuration

- **Region**: ap-southeast-2 (Sydney)
- **Device**: minimart-wa-bentley-sensor-1
- **Client ID**: minimart-wa-bentley-sensor-1
- **Data Topic**: minimart/wa/bentley/sensor/1
- **Status Topic**: minimart/wa/bentley/sensor/1/status