import { useEffect, useState, useCallback } from 'react';

export interface DeviceMetrics {
  cpu_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  memory_percent: number;
  temperature_c: number;
  uptime_seconds: number;
  timestamp: number;
}

export interface ContainerStatus {
  name: string;
  status: 'running' | 'stopped' | 'restarting';
  uptime: string;
  cpu_percent: number;
  memory_mb: number;
}

export interface TelemetryData {
  device: DeviceMetrics | null;
  containers: ContainerStatus[];
  is_raspberry_pi: boolean;
  timestamp: number;
}

interface UseTelemetryOptions {
  url?: string;
  pollInterval?: number;
  enabled?: boolean;
}

export function useTelemetry(options: UseTelemetryOptions = {}) {
  const {
    url = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000',
    pollInterval = 2000,
    enabled = true,
  } = options;

  const [telemetry, setTelemetry] = useState<TelemetryData>({
    device: null,
    containers: [],
    is_raspberry_pi: false,
    timestamp: 0,
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // History for charts
  const [cpuHistory, setCpuHistory] = useState<number[]>([]);
  const [memoryHistory, setMemoryHistory] = useState<number[]>([]);
  const [tempHistory, setTempHistory] = useState<number[]>([]);

  const fetchTelemetry = useCallback(async () => {
    try {
      const response = await fetch(`${url}/api/telemetry`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data: TelemetryData = await response.json();
      
      setTelemetry(data);
      setError(null);
      setLoading(false);

      // Update histories (keep last 30 samples)
      if (data.device) {
        setCpuHistory((prev) => [...prev.slice(-29), data.device!.cpu_percent]);
        setMemoryHistory((prev) => [...prev.slice(-29), data.device!.memory_percent]);
        setTempHistory((prev) => [...prev.slice(-29), data.device!.temperature_c]);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch telemetry');
      setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    if (!enabled) return;

    // Initial fetch
    fetchTelemetry();

    // Set up polling
    const interval = setInterval(fetchTelemetry, pollInterval);

    return () => clearInterval(interval);
  }, [enabled, pollInterval, fetchTelemetry]);

  // Helper functions
  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  const getHealthStatus = (): 'healthy' | 'warning' | 'critical' => {
    if (!telemetry.device) return 'critical';

    const { cpu_percent, memory_percent, temperature_c } = telemetry.device;

    if (cpu_percent > 90 || memory_percent > 90 || temperature_c > 80) {
      return 'critical';
    }
    if (cpu_percent > 70 || memory_percent > 75 || temperature_c > 70) {
      return 'warning';
    }
    return 'healthy';
  };

  return {
    // Data
    telemetry,
    device: telemetry.device,
    containers: telemetry.containers,
    isRaspberryPi: telemetry.is_raspberry_pi,

    // History for charts
    cpuHistory,
    memoryHistory,
    tempHistory,

    // Status
    loading,
    error,
    healthStatus: getHealthStatus(),

    // Helpers
    formatUptime,
    refetch: fetchTelemetry,
  };
}

export default useTelemetry;
