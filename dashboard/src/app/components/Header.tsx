import { Cloud, Wifi, WifiOff, Server, Activity } from "lucide-react";
import { useEffect, useState } from "react";
import { useTrackingSocket } from "../hooks";

interface HeaderProps {
  backendUrl?: string;
}

export function Header({ backendUrl = "http://localhost:5000" }: HeaderProps) {
  const { connectionState, trackingData, isConnected } = useTrackingSocket({ 
    url: backendUrl 
  });
  
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const formatDateTime = (date: Date) => {
    return date.toLocaleString("en-US", {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  };

  return (
    <div className="h-16 bg-zinc-900 border-b border-zinc-800 px-6 flex items-center justify-between">
      <div>
        <h1 className="text-xl text-white font-semibold">Command Center</h1>
        <p className="text-xs text-zinc-400 mt-0.5">{formatDateTime(currentTime)}</p>
      </div>
      
      <div className="flex items-center gap-4">
        {/* Live Stats */}
        <div className="flex items-center gap-3 px-3 py-2 bg-zinc-800/50 rounded-lg border border-zinc-700/50">
          <div className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-xs text-zinc-300 font-mono">{trackingData.fps.toFixed(1)} FPS</span>
          </div>
          <div className="w-px h-4 bg-zinc-700" />
          <div className="flex items-center gap-1.5">
            <Server className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-xs text-zinc-300">{trackingData.active_count} tracked</span>
          </div>
        </div>

        {/* Backend Connection Status */}
        <div className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
          isConnected 
            ? 'bg-emerald-500/10 border-emerald-500/20' 
            : 'bg-red-500/10 border-red-500/20'
        }`}>
          <div className="relative">
            {isConnected ? (
              <>
                <Cloud className="w-4 h-4 text-emerald-400" />
                <Wifi className="w-3 h-3 text-emerald-400 absolute -bottom-0.5 -right-0.5" />
              </>
            ) : (
              <>
                <Cloud className="w-4 h-4 text-red-400" />
                <WifiOff className="w-3 h-3 text-red-400 absolute -bottom-0.5 -right-0.5" />
              </>
            )}
          </div>
          <div className="flex flex-col">
            <span className={`text-xs font-medium ${isConnected ? 'text-emerald-400' : 'text-red-400'}`}>
              Flask Backend
            </span>
            <span className={`text-xs ${isConnected ? 'text-emerald-300/70' : 'text-red-300/70'}`}>
              {isConnected ? 'Connected' : connectionState.error || 'Disconnected'}
            </span>
          </div>
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`}></div>
        </div>
      </div>
    </div>
  );
}
