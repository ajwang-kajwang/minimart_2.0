import { Video, Maximize2, Wifi, WifiOff } from "lucide-react";
import { useState, useEffect } from "react";
import { useTrackingSocket, TrackedPerson } from "../hooks";

interface VisionFeedProps {
  backendUrl?: string;
}

export function VisionFeed({ backendUrl = "http://localhost:5000" }: VisionFeedProps) {
  const { trackingData, connectionState, isConnected, activePeople } = useTrackingSocket({
    url: backendUrl,
  });

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [imageError, setImageError] = useState(false);

  // Reset image error when connection changes
  useEffect(() => {
    if (isConnected) {
      setImageError(false);
    }
  }, [isConnected]);

  const videoFeedUrl = `${backendUrl}/video_feed`;

  const handleImageError = () => {
    setImageError(true);
  };

  const handleImageLoad = () => {
    setImageError(false);
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  // Generate bounding box color from track color
  const getBoxColor = (person: TrackedPerson) => {
    if (person.color) {
      return `rgb(${person.color[0]}, ${person.color[1]}, ${person.color[2]})`;
    }
    return "#22d3ee"; // Default cyan
  };

  return (
    <div className={`bg-zinc-900 border border-zinc-800 rounded-lg p-5 h-full flex flex-col ${isFullscreen ? 'fixed inset-4 z-50' : ''}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Video className="w-5 h-5 text-cyan-400" />
          <h2 className="text-white font-semibold">Live Computer Vision Feed</h2>
        </div>
        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <div className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs ${
            isConnected 
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
              : 'bg-red-500/10 text-red-400 border border-red-500/20'
          }`}>
            {isConnected ? (
              <>
                <Wifi className="w-3 h-3" />
                <span>Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3" />
                <span>{connectionState.error || 'Disconnected'}</span>
              </>
            )}
          </div>
          <button 
            onClick={toggleFullscreen}
            className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"
          >
            <Maximize2 className="w-4 h-4 text-zinc-400" />
          </button>
        </div>
      </div>

      <div className="flex-1 bg-zinc-950 rounded-lg border border-zinc-800 relative overflow-hidden">
        {/* Video Feed from Flask Backend */}
        {!imageError ? (
          <img
            src={videoFeedUrl}
            alt="Live Vision Feed"
            className="w-full h-full object-contain"
            onError={handleImageError}
            onLoad={handleImageLoad}
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-zinc-800 via-zinc-900 to-zinc-950 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-3 bg-zinc-800 rounded-lg flex items-center justify-center">
                <Video className="w-8 h-8 text-zinc-600" />
              </div>
              <p className="text-zinc-600 text-sm">
                {isConnected ? 'Waiting for video stream...' : 'Backend not connected'}
              </p>
              <p className="text-zinc-700 text-xs mt-1">{videoFeedUrl}</p>
            </div>
          </div>
        )}

        {/* Recording indicator */}
        <div className="absolute top-4 left-4 flex items-center gap-2 bg-red-500/20 border border-red-500/30 px-3 py-1.5 rounded-lg">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-red-500 animate-pulse' : 'bg-zinc-600'}`}></div>
          <span className={`text-xs font-medium ${isConnected ? 'text-red-400' : 'text-zinc-500'}`}>
            {isConnected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>

        {/* FPS Counter - Real data from backend */}
        <div className="absolute top-4 right-4 bg-zinc-900/80 border border-zinc-700 px-3 py-1.5 rounded-lg">
          <span className="text-zinc-300 text-xs font-mono">
            {trackingData.fps.toFixed(1)} FPS
          </span>
        </div>

        {/* Detection count - Real data */}
        <div className="absolute bottom-4 left-4 bg-zinc-900/80 border border-zinc-700 px-3 py-1.5 rounded-lg">
          <span className="text-cyan-400 text-xs font-medium">
            {activePeople.length} {activePeople.length === 1 ? 'person' : 'people'} detected
          </span>
        </div>

        {/* Active tracks list */}
        {activePeople.length > 0 && (
          <div className="absolute bottom-4 right-4 bg-zinc-900/90 border border-zinc-700 px-3 py-2 rounded-lg max-h-32 overflow-y-auto">
            <div className="text-zinc-400 text-xs mb-1.5 font-medium">Active Tracks</div>
            <div className="space-y-1">
              {activePeople.slice(0, 5).map((person) => (
                <div key={person.id} className="flex items-center gap-2 text-xs">
                  <div 
                    className="w-2 h-2 rounded-full" 
                    style={{ backgroundColor: getBoxColor(person) }}
                  />
                  <span className="text-zinc-300">ID {person.id}</span>
                  {person.real_world && (
                    <span className="text-zinc-500 font-mono">
                      ({person.real_world.x.toFixed(1)}, {person.real_world.y.toFixed(1)})
                    </span>
                  )}
                </div>
              ))}
              {activePeople.length > 5 && (
                <div className="text-zinc-500 text-xs">
                  +{activePeople.length - 5} more
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
