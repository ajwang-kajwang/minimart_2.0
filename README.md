# Minimart 2.0 - WebSocket Bridge Integration

Real-time computer vision tracking system with React dashboard integration via WebSocket.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         React Dashboard                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
│  │  VisionFeed  │ │  Bedrock     │ │   Device     │ │  Container  │ │
│  │  Component   │ │  Analysis    │ │  Telemetry   │ │   Health    │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬──────┘ │
│         │                │                │                │        │
│  ┌──────▼────────────────▼────────────────▼────────────────▼──────┐ │
│  │              useTrackingSocket / useTelemetry Hooks             │ │
│  └───────────────────────────────┬────────────────────────────────┘ │
└──────────────────────────────────┼──────────────────────────────────┘
                                   │ WebSocket + REST
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Flask Backend                                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Flask-SocketIO Server                      │   │
│  │         Events: coordinate_tracking_update, telemetry_update  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
│  │   Camera     │ │  Detection   │ │   Tracking   │ │  Telemetry  │ │
│  │   Service    │ │   Service    │ │   Service    │ │   Service   │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Start the Backend (Python/Flask)

```bash
cd minimart_2.0

# Install dependencies
pip install -r requirements.txt

# Start the backend
python main.py
```

The backend will be available at:
- API: `http://localhost:5000`
- Video Feed: `http://localhost:5000/video_feed`
- WebSocket: `ws://localhost:5000`

### 2. Start the Dashboard (React/Vite)

```bash
cd minimart_2.0/dashboard

# Install dependencies
npm install

# Start development server
npm run dev
```

The dashboard will be available at `http://localhost:5173`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info and available endpoints |
| `/video_feed` | GET | MJPEG video stream |
| `/api/coordinates` | GET | Current tracking data |
| `/api/telemetry` | GET | Device metrics + container health |
| `/api/telemetry/device` | GET | Device metrics only |
| `/api/telemetry/containers` | GET | Container health only |
| `/api/stats` | GET | Session statistics |
| `/health` | GET | Health check |

## WebSocket Events

### Server → Client

| Event | Data | Description |
|-------|------|-------------|
| `coordinate_tracking_update` | `{active_count, fps, people, timestamp}` | Real-time tracking updates (~10Hz) |
| `telemetry_update` | `{device, containers, is_raspberry_pi}` | System metrics (~0.5Hz) |

### Client → Server

| Event | Description |
|-------|-------------|
| `request_telemetry` | Manually request telemetry data |

## React Hooks

### useTrackingSocket

```typescript
const { 
  trackingData,      // Current tracking state
  isConnected,       // WebSocket connection status
  activePeople,      // Filtered active tracks
  fpsHistory,        // Historical FPS data (last 60 samples)
  countHistory,      // Historical count data (last 60 samples)
  connect,           // Manual connect function
  disconnect         // Manual disconnect function
} = useTrackingSocket({ 
  url: 'http://localhost:5000' 
});
```

### useTelemetry

```typescript
const {
  device,            // CPU, memory, temp metrics
  containers,        // Container status array
  isRaspberryPi,     // Device type detection
  loading,           // Loading state
  error,             // Error message if any
  healthStatus,      // 'healthy' | 'warning' | 'critical'
  formatUptime,      // Helper to format seconds → "2d 14h 32m"
} = useTelemetry({
  url: 'http://localhost:5000',
  pollInterval: 2000
});
```

## Configuration

### Backend Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMERA_STREAM_URL` | `tcp://127.0.0.1:8888` | Video source URL |

### Dashboard Environment Variables

Create `.env.local` in `dashboard/`:

```env
VITE_BACKEND_URL=http://localhost:5000
```

## Project Structure

```
minimart_2.0/
├── main.py                    # Flask application entry point
├── requirements.txt           # Python dependencies
├── domain/
│   └── interfaces.py          # Abstract interfaces (SOLID)
├── services/
│   ├── detection.py           # YOLO object detection
│   ├── tracking.py            # Person tracking logic
│   ├── geometry.py            # Coordinate transformation
│   └── telemetry.py           # Device metrics collection
├── infrastructure/
│   └── camera.py              # Camera hardware abstraction
└── dashboard/
    ├── package.json
    ├── src/
    │   └── app/
    │       ├── App.tsx
    │       ├── hooks/
    │       │   ├── useTrackingSocket.ts
    │       │   └── useTelemetry.ts
    │       └── components/
    │           ├── VisionFeed.tsx
    │           ├── BedrockAnalysis.tsx
    │           ├── DeviceTelemetry.tsx
    │           └── ContainerHealth.tsx
    └── .env.example
```

## Next Steps: Bedrock Integration

The `BedrockAnalysis` component is prepared for LLM integration. To connect to AWS Bedrock:

1. Add AWS SDK to backend
2. Create an analytics service endpoint
3. Replace `generateMockResponse()` with actual Bedrock calls
4. Consider streaming responses for better UX

## Development

### Testing Backend Only

```bash
# Test API endpoints
curl http://localhost:5000/api/telemetry

# Test WebSocket (using wscat)
wscat -c ws://localhost:5000/socket.io/?EIO=4&transport=websocket
```

### Testing Dashboard Only

The dashboard gracefully handles backend disconnection and shows appropriate fallback states.
