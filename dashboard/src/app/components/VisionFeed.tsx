import { Video, Maximize2 } from "lucide-react";
import { useEffect, useState } from "react";

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
  const [boxes, setBoxes] = useState<BoundingBox[]>([
    { id: 1, x: 15, y: 20, width: 25, height: 30, label: "Coca-Cola", confidence: 0.94 },
    { id: 2, x: 45, y: 25, width: 22, height: 28, label: "Sprite", confidence: 0.91 },
    { id: 3, x: 72, y: 22, width: 20, height: 32, label: "Fanta", confidence: 0.88 },
  ]);

  useEffect(() => {
    // Simulate detection updates
    const interval = setInterval(() => {
      setBoxes((prev) =>
        prev.map((box) => ({
          ...box,
          confidence: Math.max(0.8, Math.min(0.99, box.confidence + (Math.random() - 0.5) * 0.05)),
        }))
      );
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Video className="w-5 h-5 text-cyan-400" />
          <h2 className="text-white font-semibold">Live Computer Vision Feed</h2>
        </div>
        <button className="p-2 hover:bg-zinc-800 rounded-lg transition-colors">
          <Maximize2 className="w-4 h-4 text-zinc-400" />
        </button>
      </div>

      <div className="flex-1 bg-zinc-950 rounded-lg border border-zinc-800 relative overflow-hidden">
        {/* Simulated video feed background */}
        <div className="w-full h-full bg-gradient-to-br from-zinc-800 via-zinc-900 to-zinc-950 flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-3 bg-zinc-800 rounded-lg flex items-center justify-center">
              <Video className="w-8 h-8 text-zinc-600" />
            </div>
            <p className="text-zinc-600 text-sm">Shelf A - Camera 01</p>
          </div>
        </div>

        {/* Bounding boxes */}
        {boxes.map((box) => (
          <div
            key={box.id}
            className="absolute border-2 border-cyan-400 rounded"
            style={{
              left: `${box.x}%`,
              top: `${box.y}%`,
              width: `${box.width}%`,
              height: `${box.height}%`,
            }}
          >
            <div className="absolute -top-6 left-0 bg-cyan-400 text-zinc-900 px-2 py-0.5 text-xs font-medium rounded">
              {box.label} {(box.confidence * 100).toFixed(0)}%
            </div>
          </div>
        ))}

        {/* Recording indicator */}
        <div className="absolute top-4 left-4 flex items-center gap-2 bg-red-500/20 border border-red-500/30 px-3 py-1.5 rounded-lg">
          <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
          <span className="text-red-400 text-xs font-medium">LIVE</span>
        </div>

        {/* FPS Counter */}
        <div className="absolute top-4 right-4 bg-zinc-900/80 border border-zinc-700 px-3 py-1.5 rounded-lg">
          <span className="text-zinc-300 text-xs font-mono">29.97 FPS</span>
        </div>

        {/* Detection count */}
        <div className="absolute bottom-4 left-4 bg-zinc-900/80 border border-zinc-700 px-3 py-1.5 rounded-lg">
          <span className="text-cyan-400 text-xs font-medium">{boxes.length} objects detected</span>
        </div>
      </div>
    </div>
  );
}
