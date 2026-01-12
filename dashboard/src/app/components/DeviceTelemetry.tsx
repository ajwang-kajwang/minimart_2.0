import { Cpu, Thermometer, HardDrive } from "lucide-react";
import { useEffect, useState } from "react";
import { RadialBarChart, RadialBar, ResponsiveContainer } from "recharts";

export function DeviceTelemetry() {
  const [cpuLoad, setCpuLoad] = useState(45);
  const [temperature, setTemperature] = useState(58);
  const [ramUsage, setRamUsage] = useState(62);

  useEffect(() => {
    const interval = setInterval(() => {
      setCpuLoad((prev) => Math.max(20, Math.min(85, prev + (Math.random() - 0.5) * 10)));
      setTemperature((prev) => Math.max(45, Math.min(75, prev + (Math.random() - 0.5) * 5)));
      setRamUsage((prev) => Math.max(40, Math.min(90, prev + (Math.random() - 0.5) * 8)));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

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
    if (ramUsage > 80) return "bg-red-500";
    if (ramUsage > 65) return "bg-amber-500";
    return "bg-cyan-500";
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <Cpu className="w-5 h-5 text-blue-400" />
        <h2 className="text-white font-semibold">Device Telemetry</h2>
      </div>

      <div className="text-xs text-zinc-500 mb-4 flex items-center gap-2">
        <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
        <span>Raspberry Pi 5 - 8GB RAM</span>
      </div>

      {/* CPU Load - Radial Gauge */}
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
        <div className="h-32 -ml-4">
          <ResponsiveContainer width="100%" height="100%">
            <RadialBarChart
              cx="50%"
              cy="50%"
              innerRadius="70%"
              outerRadius="90%"
              barSize={12}
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
      </div>

      {/* Temperature - Linear Bar */}
      <div className="mb-5">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Thermometer className="w-4 h-4 text-zinc-400" />
            <span className="text-sm text-zinc-300">Temperature</span>
          </div>
          <span className="text-sm font-mono text-zinc-400">{temperature.toFixed(1)}°C</span>
        </div>
        <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className={`h-full ${getTempColor()} transition-all duration-500 rounded-full`}
            style={{ width: `${(temperature / 85) * 100}%` }}
          ></div>
        </div>
        <div className="flex justify-between text-xs text-zinc-600 mt-1">
          <span>0°C</span>
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
            {((ramUsage / 100) * 8).toFixed(2)} / 8.00 GB
          </span>
        </div>
        <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className={`h-full ${getRamColor()} transition-all duration-500 rounded-full`}
            style={{ width: `${ramUsage}%` }}
          ></div>
        </div>
        <div className="flex justify-between text-xs text-zinc-600 mt-1">
          <span>0%</span>
          <span>100%</span>
        </div>
      </div>
    </div>
  );
}
