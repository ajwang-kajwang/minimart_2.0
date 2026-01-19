# Dashboard - Jetson Edition

The React dashboard is identical to the Raspberry Pi version. 

## Setup

If you already have the dashboard from the RP5 version, copy over your `src/` directory:

```bash
# From your original minimart_2.0 project
cp -r minimart_2.0/dashboard/src/ minimart_jetson/dashboard/

# Or copy specific files
cp -r minimart_2.0/dashboard/src/app/ minimart_jetson/dashboard/src/app/
```

Then install and run:

```bash
cd dashboard
npm install
npm run dev
```

## Environment

Create `.env.local`:

```env
VITE_BACKEND_URL=http://<jetson-ip>:5000
```

## Access

Dashboard: `http://<jetson-ip>:5173`
Backend API: `http://<jetson-ip>:5000`
Video Feed: `http://<jetson-ip>:5000/video_feed`

## Jetson-Specific Changes

The telemetry display will show Jetson-specific metrics:
- GPU utilization and frequency
- TensorRT inference timing
- Power consumption
- JetPack version
- NVPModel mode
