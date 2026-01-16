import { Video, Maximize2, Activity } from "lucide-react";
import { useEffect, useState } from "react";
import { socket } from "../services/socket"; // Import shared socket

interface BoundingBox {
  id: number;
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
  confidence: number;
}

export function VisionFeed() {
  const [boxes, setBoxes] = useState<BoundingBox[]>([]);
  const [fps, setFps] = useState(0);
  const [activeCount, setActiveCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);

  // Dynamic Video URL: Points to Flask on port 5000 regardless of where React is running
  const videoUrl = `http://${window.location.hostname}:5000/video_feed`;

  useEffect(() => {
    function onConnect() {
      setIsConnected(true);
    }

    function onDisconnect() {
      setIsConnected(false);
    }

    function onTrackingUpdate(data: any) {
      setFps(data.fps);
      setActiveCount(data.active_count);

      // Map Python backend data to React state
      // Backend sends: { id, x, y, width, height, confidence, ... } (pixels)
      // Frontend expects % for responsive overlay
      const mappedBoxes = data.people.map((p: any) => ({
        id: p.id,
        // Assuming 640x640 input resolution from Hailo/Camera. 
        // Adjust 640 if your camera resolution differs.
        x: (p.x / 640) * 100, 
        y: (p.y / 640) * 100,
        width: (p.width / 640) * 100,
        height: (p.height / 640) * 100,
        label: "Person",
        confidence: p.confidence
      }));
      setBoxes(mappedBoxes);
    }

    // Attach listeners
    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    socket.on("coordinate_tracking_update", onTrackingUpdate);

    // Cleanup listeners on unmount
    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      socket.off("coordinate_tracking_update", onTrackingUpdate);
    };
  }, []);

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Video className="w-5 h-5 text-cyan-400" />
          <h2 className="text-white font-semibold">Live Computer Vision Feed</h2>
          {isConnected ? (
            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 rounded-full border border-emerald-500/20">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-medium text-emerald-500">LIVE</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-red-500/10 rounded-full border border-red-500/20">
              <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
              <span className="text-[10px] font-medium text-red-500">OFFLINE</span>
            </div>
          )}
        </div>
        <button className="p-2 hover:bg-zinc-800 rounded-lg transition-colors">
          <Maximize2 className="w-4 h-4 text-zinc-400" />
        </button>
      </div>

      <div className="flex-1 bg-zinc-950 rounded-lg border border-zinc-800 relative overflow-hidden group">
        {/* Real Video Feed */}
        <img 
          src={videoUrl} 
          alt="Live Stream"
          className="absolute inset-0 w-full h-full object-cover opacity-90"
        />

        {/* Bounding Box Overlay */}
        {boxes.map((box) => (
          <div
            key={box.id}
            className="absolute border-2 border-cyan-400 rounded transition-all duration-75 ease-linear"
            style={{
              left: `${box.x}%`,
              top: `${box.y}%`,
              width: `${box.width}%`,
              height: `${box.height}%`,
            }}
          >
            <div className="absolute -top-6 left-0 bg-cyan-400 text-zinc-900 px-1.5 py-0.5 text-[10px] font-bold rounded shadow-sm whitespace-nowrap">
              ID: {box.id} • {(box.confidence * 100).toFixed(0)}%
            </div>
          </div>
        ))}

        {/* HUD Elements */}
        <div className="absolute top-4 right-4 flex flex-col gap-2 items-end">
          <div className="bg-black/60 backdrop-blur-md border border-white/10 px-3 py-1.5 rounded-lg flex items-center gap-2">
            <Activity className="w-3 h-3 text-emerald-400" />
            <span className="text-white text-xs font-mono">{fps.toFixed(1)} FPS</span>
          </div>
        </div>

        <div className="absolute bottom-4 left-4">
          <div className="bg-black/60 backdrop-blur-md border border-white/10 px-3 py-1.5 rounded-lg">
            <span className="text-cyan-400 text-xs font-medium">{activeCount} Objects Tracked</span>
          </div>
        </div>
      </div>
    </div>
  );
}