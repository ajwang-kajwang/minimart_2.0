import { Cloud, Wifi } from "lucide-react";
import { useEffect, useState } from "react";

export function Header() {
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
        <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
          <div className="relative">
            <Cloud className="w-4 h-4 text-emerald-400" />
            <Wifi className="w-3 h-3 text-emerald-400 absolute -bottom-0.5 -right-0.5" />
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-emerald-400 font-medium">AWS IoT Core</span>
            <span className="text-xs text-emerald-300/70">Connected</span>
          </div>
          <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
        </div>
      </div>
    </div>
  );
}
