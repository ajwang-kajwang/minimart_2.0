import { Brain, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

interface AnalysisEntry {
  id: number;
  timestamp: string;
  message: string;
  type: "info" | "warning" | "success";
}

export function BedrockAnalysis() {
  const [entries, setEntries] = useState<AnalysisEntry[]>([
    {
      id: 1,
      timestamp: "14:32:45",
      message: "Customer picked up Coca-Cola from Shelf A, position 3",
      type: "info",
    },
    {
      id: 2,
      timestamp: "14:32:38",
      message: "Shelf B appears disorganized - Products not aligned properly",
      type: "warning",
    },
    {
      id: 3,
      timestamp: "14:32:21",
      message: "Inventory levels optimal for current time period",
      type: "success",
    },
    {
      id: 4,
      timestamp: "14:32:05",
      message: "Customer behavior analysis: Extended browsing at Shelf C",
      type: "info",
    },
  ]);

  useEffect(() => {
    // Simulate new AI insights
    const messages = [
      { message: "New customer detected in zone 2", type: "info" as const },
      { message: "Low stock alert: Sprite - 2 units remaining on Shelf A", type: "warning" as const },
      { message: "Customer completed purchase decision at Shelf A", type: "success" as const },
      { message: "Temperature anomaly detected - cooling system check recommended", type: "warning" as const },
      { message: "Shelf restocking recommended for optimal presentation", type: "info" as const },
    ];

    const interval = setInterval(() => {
      const randomMessage = messages[Math.floor(Math.random() * messages.length)];
      const now = new Date();
      const timestamp = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;

      setEntries((prev) => [
        {
          id: Date.now(),
          timestamp,
          ...randomMessage,
        },
        ...prev.slice(0, 7),
      ]);
    }, 8000);

    return () => clearInterval(interval);
  }, []);

  const getTypeColor = (type: string) => {
    switch (type) {
      case "warning":
        return "border-amber-500/20 bg-amber-500/5";
      case "success":
        return "border-emerald-500/20 bg-emerald-500/5";
      default:
        return "border-cyan-500/20 bg-cyan-500/5";
    }
  };

  const getTypeDot = (type: string) => {
    switch (type) {
      case "warning":
        return "bg-amber-400";
      case "success":
        return "bg-emerald-400";
      default:
        return "bg-cyan-400";
    }
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-5 h-5 text-purple-400" />
        <h2 className="text-white font-semibold">AWS Bedrock Analysis</h2>
        <Sparkles className="w-4 h-4 text-purple-400 ml-1" />
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-2">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className={`border rounded-lg p-3 ${getTypeColor(entry.type)} transition-all hover:border-opacity-40`}
          >
            <div className="flex items-start gap-3">
              <div className={`w-2 h-2 ${getTypeDot(entry.type)} rounded-full mt-1.5 flex-shrink-0`}></div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-zinc-300">{entry.message}</p>
                <p className="text-xs text-zinc-500 mt-1 font-mono">{entry.timestamp}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-zinc-800">
        <div className="flex items-center justify-between text-xs text-zinc-500">
          <span>AI Model: Claude 3.5 Sonnet</span>
          <div className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-pulse"></div>
            <span className="text-purple-400">Processing</span>
          </div>
        </div>
      </div>
    </div>
  );
}
