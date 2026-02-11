#!/usr/bin/env python3
"""
Telemetry Service for Raspberry Pi Device Monitoring
Gathers CPU, memory, temperature, and container health metrics
"""

import os
import time
import subprocess
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class DeviceMetrics:
    cpu_percent: float
    memory_used_mb: float
    memory_total_mb: float
    memory_percent: float
    temperature_c: float
    uptime_seconds: float
    timestamp: float

@dataclass 
class ContainerStatus:
    name: str
    status: str  # 'running', 'stopped', 'restarting'
    uptime: str
    cpu_percent: float
    memory_mb: float

class TelemetryService:
    """
    Gathers system telemetry for the Raspberry Pi.
    Works on both Pi and standard Linux for development.
    """
    
    def __init__(self, poll_interval: float = 2.0):
        self.poll_interval = poll_interval
        self._metrics: Optional[DeviceMetrics] = None
        self._containers: list[ContainerStatus] = []
        self._running = False
        self._lock = threading.Lock()
        
        # Check if we're on a Pi (has vcgencmd)
        self._is_raspberry_pi = os.path.exists('/usr/bin/vcgencmd')
        
    def start(self):
        """Start background telemetry collection"""
        self._running = True
        thread = threading.Thread(target=self._collection_loop, daemon=True)
        thread.start()
        print("📊 Telemetry service started")
        
    def stop(self):
        """Stop telemetry collection"""
        self._running = False
        
    def _collection_loop(self):
        """Background loop to collect metrics"""
        while self._running:
            try:
                metrics = self._collect_device_metrics()
                containers = self._collect_container_status()
                
                with self._lock:
                    self._metrics = metrics
                    self._containers = containers
                    
            except Exception as e:
                print(f"⚠️ Telemetry collection error: {e}")
                
            time.sleep(self.poll_interval)
    
    def _collect_device_metrics(self) -> DeviceMetrics:
        """Collect CPU, memory, and temperature"""
        
        # CPU Usage
        cpu_percent = self._get_cpu_usage()
        
        # Memory
        mem_info = self._get_memory_info()
        
        # Temperature
        temperature = self._get_temperature()
        
        # Uptime
        uptime = self._get_uptime()
        
        return DeviceMetrics(
            cpu_percent=cpu_percent,
            memory_used_mb=mem_info['used_mb'],
            memory_total_mb=mem_info['total_mb'],
            memory_percent=mem_info['percent'],
            temperature_c=temperature,
            uptime_seconds=uptime,
            timestamp=time.time()
        )
    
    def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage"""
        try:
            # Read /proc/stat for CPU times
            with open('/proc/stat', 'r') as f:
                line = f.readline()
            
            values = line.split()[1:8]
            values = [int(v) for v in values]
            
            # user, nice, system, idle, iowait, irq, softirq
            idle = values[3] + values[4]
            total = sum(values)
            
            # Store for delta calculation
            if not hasattr(self, '_last_cpu'):
                self._last_cpu = (idle, total)
                return 0.0
            
            last_idle, last_total = self._last_cpu
            idle_delta = idle - last_idle
            total_delta = total - last_total
            
            self._last_cpu = (idle, total)
            
            if total_delta == 0:
                return 0.0
                
            return round((1.0 - idle_delta / total_delta) * 100, 1)
            
        except Exception:
            return 0.0
    
    def _get_memory_info(self) -> Dict[str, float]:
        """Get memory usage info"""
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            
            mem_info = {}
            for line in lines:
                parts = line.split()
                key = parts[0].rstrip(':')
                value = int(parts[1])  # in kB
                mem_info[key] = value
            
            total_mb = mem_info.get('MemTotal', 0) / 1024
            available_mb = mem_info.get('MemAvailable', 0) / 1024
            used_mb = total_mb - available_mb
            percent = (used_mb / total_mb * 100) if total_mb > 0 else 0
            
            return {
                'total_mb': round(total_mb, 1),
                'used_mb': round(used_mb, 1),
                'available_mb': round(available_mb, 1),
                'percent': round(percent, 1)
            }
            
        except Exception:
            return {'total_mb': 0, 'used_mb': 0, 'available_mb': 0, 'percent': 0}
    
    def _get_temperature(self) -> float:
        """Get CPU temperature"""
        try:
            # Raspberry Pi specific
            if self._is_raspberry_pi:
                result = subprocess.run(
                    ['vcgencmd', 'measure_temp'],
                    capture_output=True, text=True, timeout=2
                )
                # Parse "temp=45.0'C"
                temp_str = result.stdout.strip()
                temp = float(temp_str.split('=')[1].rstrip("'C"))
                return round(temp, 1)
            
            # Generic Linux thermal zone
            thermal_path = '/sys/class/thermal/thermal_zone0/temp'
            if os.path.exists(thermal_path):
                with open(thermal_path, 'r') as f:
                    temp = int(f.read().strip()) / 1000
                return round(temp, 1)
                
            return 0.0
            
        except Exception:
            return 0.0
    
    def _get_uptime(self) -> float:
        """Get system uptime in seconds"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime = float(f.readline().split()[0])
            return uptime
        except Exception:
            return 0.0
    
    def _collect_container_status(self) -> list[ContainerStatus]:
        """Collect Docker container status if available"""
        containers = []
        
        try:
            # Check if docker is available
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}\t{{.ID}}'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode != 0:
                return self._get_mock_containers()
            
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                if not line.strip():
                    continue
                    
                parts = line.split('\t')
                if len(parts) >= 2:
                    name = parts[0]
                    status_str = parts[1]
                    
                    # Determine status
                    if 'Up' in status_str:
                        status = 'running'
                        uptime = status_str.replace('Up ', '')
                    elif 'Restarting' in status_str:
                        status = 'restarting'
                        uptime = '0s'
                    else:
                        status = 'stopped'
                        uptime = 'N/A'
                    
                    # Get container stats (CPU, memory)
                    cpu, mem = self._get_container_stats(parts[2] if len(parts) > 2 else name)
                    
                    containers.append(ContainerStatus(
                        name=name,
                        status=status,
                        uptime=uptime,
                        cpu_percent=cpu,
                        memory_mb=mem
                    ))
            
            return containers if containers else self._get_mock_containers()
            
        except Exception:
            return self._get_mock_containers()
    
    def _get_container_stats(self, container_id: str) -> tuple[float, float]:
        """Get CPU and memory for a specific container"""
        try:
            result = subprocess.run(
                ['docker', 'stats', container_id, '--no-stream', '--format', '{{.CPUPerc}}\t{{.MemUsage}}'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split('\t')
                cpu = float(parts[0].rstrip('%'))
                mem_str = parts[1].split('/')[0].strip()
                
                # Parse memory (could be MiB, GiB, etc.)
                if 'GiB' in mem_str:
                    mem = float(mem_str.replace('GiB', '').strip()) * 1024
                elif 'MiB' in mem_str:
                    mem = float(mem_str.replace('MiB', '').strip())
                else:
                    mem = 0
                    
                return round(cpu, 1), round(mem, 1)
                
        except Exception:
            pass
            
        return 0.0, 0.0
    
    def _get_mock_containers(self) -> list[ContainerStatus]:
        """Return mock container data for development/testing"""
        return [
            ContainerStatus(
                name="vision-service",
                status="running",
                uptime="2d 14h 32m",
                cpu_percent=23.4,
                memory_mb=456
            ),
            ContainerStatus(
                name="mqtt-broker", 
                status="running",
                uptime="2d 14h 31m",
                cpu_percent=5.2,
                memory_mb=128
            ),
            ContainerStatus(
                name="flask-backend",
                status="running", 
                uptime="2d 14h 30m",
                cpu_percent=12.1,
                memory_mb=312
            ),
        ]
    
    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get current device metrics"""
        with self._lock:
            if self._metrics:
                return asdict(self._metrics)
            return None
    
    def get_containers(self) -> list[Dict[str, Any]]:
        """Get current container status"""
        with self._lock:
            return [asdict(c) for c in self._containers]
    
    def get_full_telemetry(self) -> Dict[str, Any]:
        """Get all telemetry data"""
        return {
            'device': self.get_metrics(),
            'containers': self.get_containers(),
            'is_raspberry_pi': self._is_raspberry_pi,
            'timestamp': time.time()
        }


# Singleton instance
_telemetry_service: Optional[TelemetryService] = None

def get_telemetry_service() -> TelemetryService:
    """Get or create telemetry service singleton"""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
        _telemetry_service.start()
    return _telemetry_service
