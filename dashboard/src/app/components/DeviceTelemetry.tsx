import { Cpu, Thermometer, HardDrive, Server, AlertTriangle } from "lucide-react";
import { useTelemetry } from "../hooks";
import { RadialBarChart, RadialBar, ResponsiveContainer, LineChart, Line, YAxis } from "recharts";

interface DeviceTelemetryProps {
  backendUrl?: string;
}

export function DeviceTelemetry({ backendUrl = "http://localhost:5000" }: DeviceTelemetryProps) {
  const { 
    device, 
    isRaspberryPi, 
    loading, 
    error, 
    cpuHistory,
    formatUptime,
    healthStatus 
  } = useTelemetry({ url: backendUrl });

  // Fallback values when loading or error
  const cpuLoad = device?.cpu_percent ?? 0;
  const temperature = device?.temperature_c ?? 0;
  const memoryUsed = device?.memory_used_mb ?? 0;
  const memoryTotal = device?.memory_total_mb ?? 8192;
  const memoryPercent = device?.memory_percent ?? 0;
  const uptime = device?.uptime_seconds ?? 0;

  const cpuData = [{ name: "CPU", value: cpuLoad, fill: "#22d3ee" }];

  const getCpuColor = () => {
    if (cpuLoad > 75) return "text-red-400";
    if (cpuLoad > 50) return "text-amber-400";
    return "text-emerald-400";
  };

  const getTempColor = () => {
    if (temperature > 70) return "bg-red-500";
    if (temperature > 60) return "bg-amber-500";
    return "bg-emerald-500";
  };

  const getRamColor = () => {
    if (memoryPercent > 80) return "bg-red-500";
    if (memoryPercent > 65) return "bg-amber-500";
    return "bg-cyan-500";
  };

  const getHealthIcon = () => {
    switch (healthStatus) {
      case 'critical':
        return <AlertTriangle className="w-4 h-4 text-red-400" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      default:
        return <Server className="w-4 h-4 text-emerald-400" />;
    }
  };

  // Prepare sparkline data
  const sparklineData = cpuHistory.map((value, index) => ({ value, index }));

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Cpu className="w-5 h-5 text-blue-400" />
          <h2 className="text-white font-semibold">Device Telemetry</h2>
        </div>
        {getHealthIcon()}
      </div>

      <div className="text-xs text-zinc-500 mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${error ? 'bg-red-400' : 'bg-blue-400'}`}></div>
          <span>{isRaspberryPi ? 'Raspberry Pi 5' : 'Linux Server'} - {(memoryTotal / 1024).toFixed(0)}GB RAM</span>
        </div>
        {device && (
          <span className="text-zinc-600 font-mono">
            Up: {formatUptime(uptime)}
          </span>
        )}
      </div>

      {error ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto mb-2" />
            <p className="text-zinc-400 text-sm">Cannot connect to backend</p>
            <p className="text-zinc-600 text-xs mt-1">{error}</p>
          </div>
        </div>
      ) : (
        <>
          {/* CPU Load - Radial Gauge with Sparkline */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-zinc-400" />
                <span className="text-sm text-zinc-300">CPU Load</span>
              </div>
              <span className={`text-sm font-mono font-semibold ${getCpuColor()}`}>
                {cpuLoad.toFixed(1)}%
              </span>
            </div>
            
            <div className="flex items-center gap-4">
              {/* Radial gauge */}
              <div className="h-24 w-24 -ml-2">
                <ResponsiveContainer width="100%" height="100%">
                  <RadialBarChart
                    cx="50%"
                    cy="50%"
                    innerRadius="70%"
                    outerRadius="90%"
                    barSize={10}
                    data={cpuData}
                    startAngle={180}
                    endAngle={0}
                  >
                    <RadialBar
                      background={{ fill: "#27272a" }}
                      dataKey="value"
                      cornerRadius={10}
                    />
                  </RadialBarChart>
                </ResponsiveContainer>
              </div>
              
              {/* Sparkline */}
              {sparklineData.length > 2 && (
                <div className="flex-1 h-16">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={sparklineData}>
                      <YAxis domain={[0, 100]} hide />
                      <Line 
                        type="monotone" 
                        dataKey="value" 
                        stroke="#22d3ee" 
                        strokeWidth={1.5}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>

          {/* Temperature - Linear Bar */}
          <div className="mb-5">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Thermometer className="w-4 h-4 text-zinc-400" />
                <span className="text-sm text-zinc-300">Temperature</span>
              </div>
              <span className="text-sm font-mono text-zinc-400">
                {temperature > 0 ? `${temperature.toFixed(1)}°C` : 'N/A'}
              </span>
            </div>
            <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className={`h-full ${getTempColor()} transition-all duration-500 rounded-full`}
                style={{ width: `${Math.min((temperature / 85) * 100, 100)}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-xs text-zinc-600 mt-1">
              <span>0°C</span>
              <span className="text-zinc-500">Safe: &lt;70°C</span>
              <span>85°C</span>
            </div>
          </div>

          {/* RAM Usage - Linear Bar */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-zinc-400" />
                <span className="text-sm text-zinc-300">RAM Usage</span>
              </div>
              <span className="text-sm font-mono text-zinc-400">
                {(memoryUsed / 1024).toFixed(2)} / {(memoryTotal / 1024).toFixed(2)} GB
              </span>
            </div>
            <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className={`h-full ${getRamColor()} transition-all duration-500 rounded-full`}
                style={{ width: `${memoryPercent}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-xs text-zinc-600 mt-1">
              <span>0%</span>
              <span>{memoryPercent.toFixed(0)}%</span>
              <span>100%</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
