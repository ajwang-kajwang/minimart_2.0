import { Container, CheckCircle2, XCircle, Clock } from "lucide-react";
import { useEffect, useState } from "react";

interface ContainerStatus {
  name: string;
  status: "running" | "stopped" | "restarting";
  uptime: string;
  cpu: number;
  memory: string;
}

export function ContainerHealth() {
  const [containers, setContainers] = useState<ContainerStatus[]>([
    {
      name: "Vision-Service",
      status: "running",
      uptime: "2d 14h 32m",
      cpu: 23.4,
      memory: "456 MB",
    },
    {
      name: "MQTT-Broker",
      status: "running",
      uptime: "2d 14h 31m",
      cpu: 5.2,
      memory: "128 MB",
    },
    {
      name: "AWS-IoT-Client",
      status: "running",
      uptime: "2d 14h 30m",
      cpu: 8.7,
      memory: "89 MB",
    },
    {
      name: "Database-Service",
      status: "running",
      uptime: "2d 14h 29m",
      cpu: 12.1,
      memory: "312 MB",
    },
  ]);

  useEffect(() => {
    const interval = setInterval(() => {
      setContainers((prev) =>
        prev.map((container) => ({
          ...container,
          cpu: Math.max(1, Math.min(50, container.cpu + (Math.random() - 0.5) * 5)),
        }))
      );
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case "stopped":
        return <XCircle className="w-4 h-4 text-red-400" />;
      case "restarting":
        return <Clock className="w-4 h-4 text-amber-400 animate-spin" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "running":
        return "text-emerald-400";
      case "stopped":
        return "text-red-400";
      case "restarting":
        return "text-amber-400";
      default:
        return "text-zinc-400";
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case "running":
        return "bg-emerald-500/10 border-emerald-500/20";
      case "stopped":
        return "bg-red-500/10 border-red-500/20";
      case "restarting":
        return "bg-amber-500/10 border-amber-500/20";
      default:
        return "bg-zinc-500/10 border-zinc-500/20";
    }
  };

  const runningCount = containers.filter((c) => c.status === "running").length;

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Container className="w-5 h-5 text-indigo-400" />
          <h2 className="text-white font-semibold">Container Health</h2>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
          <span className="text-zinc-400">
            {runningCount}/{containers.length} Running
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-2">
        {containers.map((container, index) => (
          <div
            key={index}
            className={`border rounded-lg p-4 ${getStatusBg(container.status)} transition-all hover:border-opacity-40`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                {getStatusIcon(container.status)}
                <span className="text-white font-medium text-sm">{container.name}</span>
              </div>
              <span className={`text-xs uppercase font-semibold ${getStatusColor(container.status)}`}>
                {container.status}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-4 text-xs">
              <div>
                <p className="text-zinc-500 mb-1">Uptime</p>
                <p className="text-zinc-300 font-mono">{container.uptime}</p>
              </div>
              <div>
                <p className="text-zinc-500 mb-1">CPU</p>
                <p className="text-zinc-300 font-mono">{container.cpu.toFixed(1)}%</p>
              </div>
              <div>
                <p className="text-zinc-500 mb-1">Memory</p>
                <p className="text-zinc-300 font-mono">{container.memory}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-zinc-800">
        <div className="flex items-center justify-between text-xs text-zinc-500">
          <span>Docker Engine v24.0.7</span>
          <div className="flex items-center gap-1">
            <Container className="w-3 h-3" />
            <span>Orchestration: Active</span>
          </div>
        </div>
      </div>
    </div>
  );
}
