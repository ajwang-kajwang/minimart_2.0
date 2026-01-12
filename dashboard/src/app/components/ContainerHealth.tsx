import { Container, CheckCircle2, XCircle, Clock, RefreshCw, AlertTriangle } from "lucide-react";
import { useTelemetry, ContainerStatus } from "../hooks";

interface ContainerHealthProps {
  backendUrl?: string;
}

export function ContainerHealth({ backendUrl = "http://localhost:5000" }: ContainerHealthProps) {
  const { containers, loading, error, refetch } = useTelemetry({ url: backendUrl });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case "stopped":
        return <XCircle className="w-4 h-4 text-red-400" />;
      case "restarting":
        return <Clock className="w-4 h-4 text-amber-400 animate-spin" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-zinc-400" />;
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

  // Format container name for display
  const formatName = (name: string) => {
    return name
      .replace(/_/g, '-')
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Container className="w-5 h-5 text-indigo-400" />
          <h2 className="text-white font-semibold">Container Health</h2>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={refetch}
            className="p-1.5 hover:bg-zinc-800 rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-zinc-500 hover:text-zinc-300 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <div className="flex items-center gap-2 text-xs">
            <div className={`w-2 h-2 rounded-full ${runningCount === containers.length ? 'bg-emerald-400' : 'bg-amber-400'}`}></div>
            <span className="text-zinc-400">
              {runningCount}/{containers.length} Running
            </span>
          </div>
        </div>
      </div>

      {error ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto mb-2" />
            <p className="text-zinc-400 text-sm">Cannot fetch container status</p>
            <p className="text-zinc-600 text-xs mt-1">{error}</p>
          </div>
        </div>
      ) : containers.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Container className="w-8 h-8 text-zinc-600 mx-auto mb-2" />
            <p className="text-zinc-500 text-sm">No containers found</p>
            <p className="text-zinc-600 text-xs mt-1">Docker may not be running</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-3 pr-2">
          {containers.map((container, index) => (
            <ContainerCard key={index} container={container} />
          ))}
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-zinc-800">
        <div className="flex items-center justify-between text-xs text-zinc-500">
          <span>Docker Engine</span>
          <div className="flex items-center gap-1">
            <Container className="w-3 h-3" />
            <span>Orchestration: {containers.length > 0 ? 'Active' : 'Unknown'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Separate component for each container card
function ContainerCard({ container }: { container: ContainerStatus }) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case "stopped":
        return <XCircle className="w-4 h-4 text-red-400" />;
      case "restarting":
        return <RefreshCw className="w-4 h-4 text-amber-400 animate-spin" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-zinc-400" />;
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

  // Format container name for display
  const formatName = (name: string) => {
    return name
      .replace(/_/g, '-')
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className={`border rounded-lg p-4 ${getStatusBg(container.status)} transition-all hover:border-opacity-40`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {getStatusIcon(container.status)}
          <span className="text-white font-medium text-sm">{formatName(container.name)}</span>
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
          <p className={`font-mono ${container.cpu_percent > 50 ? 'text-amber-400' : 'text-zinc-300'}`}>
            {container.cpu_percent.toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-zinc-500 mb-1">Memory</p>
          <p className="text-zinc-300 font-mono">
            {container.memory_mb >= 1024 
              ? `${(container.memory_mb / 1024).toFixed(1)} GB`
              : `${container.memory_mb.toFixed(0)} MB`
            }
          </p>
        </div>
      </div>
    </div>
  );
}
