'use client';

import { useState, useEffect } from 'react';
import { Video, Activity, WifiOff } from 'lucide-react';

interface LiveStreamProps {
  backendUrl?: string;
}

export default function LiveStream({ backendUrl = 'http://localhost:5000' }: LiveStreamProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [fps, setFps] = useState(0);
  const [activeCount, setActiveCount] = useState(0);
  const streamUrl = `${backendUrl}/video_feed`;

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/status`);
        if (res.ok) {
            const data = await res.json();
            setIsConnected(true);
            setFps(data.fps || 0);
            setActiveCount(data.active_tracks || 0);
        } else {
            setIsConnected(false);
        }
      } catch (e) {
        setIsConnected(false);
      }
    };

    const interval = setInterval(checkHealth, 2000);
    checkHealth();
    return () => clearInterval(interval);
  }, [backendUrl]);

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Video className="h-5 w-5 text-teal-600" />
          <h2 className="text-lg font-bold text-gray-800">Live Vision Feed</h2>
          {isConnected ? (
            <span className="flex items-center gap-1 text-xs font-medium text-green-600 bg-green-50 px-2 py-0.5 rounded-full border border-green-100">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              LIVE
            </span>
          ) : (
             <span className="flex items-center gap-1 text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full border border-red-100">
              <WifiOff className="w-3 h-3" /> OFFLINE
            </span>
          )}
        </div>
      </div>

      <div className="relative flex-1 bg-black rounded-lg overflow-hidden group min-h-[300px]">
        <img 
          src={streamUrl} 
          alt="Live Camera Feed"
          className="absolute inset-0 w-full h-full object-cover"
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
        />
        {!isConnected && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 bg-gray-900/90 z-10">
                <WifiOff className="w-12 h-12 mb-2 opacity-50" />
                <p>Connecting to Camera Source...</p>
                <p className="text-xs mt-1 text-gray-600">Ensure Backend is on Port 5000</p>
            </div>
        )}
        <div className="absolute top-3 right-3 flex flex-col gap-2 items-end">
            <div className="bg-black/60 backdrop-blur-sm text-white text-xs px-2 py-1 rounded flex items-center gap-2">
                <Activity className="w-3 h-3 text-green-400" />
                <span className="font-mono">{fps.toFixed(1)} FPS</span>
            </div>
        </div>
        <div className="absolute bottom-3 left-3">
             <div className="bg-black/60 backdrop-blur-sm text-white text-xs px-2 py-1 rounded">
                <span className="text-teal-400 font-bold">{activeCount}</span> Objects
            </div>
        </div>
      </div>
    </div>
  );
}