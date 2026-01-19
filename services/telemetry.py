"""
Telemetry Service - Jetson Orin Nano Metrics via jetson-stats
"""

import threading
import time
import subprocess
import os
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List

# Try to import jetson-stats
try:
    from jtop import jtop
    HAS_JTOP = True
except ImportError:
    HAS_JTOP = False
    print("⚠️  jetson-stats not installed. Run: sudo pip3 install jetson-stats")


@dataclass
class JetsonMetrics:
    """Jetson-specific device metrics"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    gpu_percent: float
    gpu_freq_mhz: int
    temperature_cpu: float
    temperature_gpu: float
    temperature_board: float
    power_current_mw: int
    power_average_mw: int
    jetpack_version: str
    nvpmodel_mode: str
    uptime_seconds: int


@dataclass
class ContainerStatus:
    """Docker container status"""
    name: str
    status: str
    uptime: str
    cpu_percent: float
    memory_mb: float


class TelemetryService:
    """
    Collects Jetson device metrics and Docker container status.
    Uses jetson-stats (jtop) for hardware metrics.
    """
    
    def __init__(self, poll_interval: float = 2.0):
        self.poll_interval = poll_interval
        self._metrics: Optional[JetsonMetrics] = None
        self._containers: List[ContainerStatus] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._is_jetson = self._detect_jetson()
        
        if self._is_jetson:
            print("✅ Jetson platform detected")
        else:
            print("⚠️  Not running on Jetson - using mock telemetry")
    
    def _detect_jetson(self) -> bool:
        """Detect if running on Jetson hardware"""
        try:
            with open('/etc/nv_tegra_release', 'r') as f:
                return 'NVIDIA' in f.read()
        except FileNotFoundError:
            pass
        
        try:
            result = subprocess.run(
                ['cat', '/proc/device-tree/model'],
                capture_output=True, text=True, timeout=5
            )
            return 'Jetson' in result.stdout
        except Exception:
            pass
        
        return False
    
    def start(self):
        """Start background telemetry collection"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._thread.start()
        print(f"📊 Telemetry service started (poll: {self.poll_interval}s)")
    
    def stop(self):
        """Stop telemetry collection"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _collection_loop(self):
        """Background thread for collecting metrics"""
        while self._running:
            try:
                if self._is_jetson and HAS_JTOP:
                    self._collect_jetson_metrics()
                else:
                    self._collect_mock_metrics()
                
                self._collect_container_metrics()
            except Exception as e:
                print(f"⚠️  Telemetry collection error: {e}")
            
            time.sleep(self.poll_interval)
    
    def _collect_jetson_metrics(self):
        """Collect real Jetson metrics via jtop"""
        try:
            with jtop() as jetson:
                # Wait for first reading
                jetson.attach(lambda _: None)
                
                stats = jetson.stats
                
                # CPU metrics
                cpu_percent = sum(jetson.cpu.get('cpu', {}).values()) / len(jetson.cpu.get('cpu', {})) if jetson.cpu.get('cpu') else 0
                
                # Memory metrics
                ram = jetson.memory.get('RAM', {})
                mem_used = ram.get('used', 0) / (1024 * 1024)  # Convert to MB
                mem_total = ram.get('total', 1) / (1024 * 1024)
                mem_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0
                
                # GPU metrics
                gpu_info = jetson.gpu
                gpu_percent = gpu_info.get('load', 0) if gpu_info else 0
                gpu_freq = gpu_info.get('freq', {}).get('cur', 0) if gpu_info else 0
                
                # Temperature
                temps = jetson.temperature
                temp_cpu = temps.get('CPU', temps.get('cpu', 0))
                temp_gpu = temps.get('GPU', temps.get('gpu', 0))
                temp_board = temps.get('AO', temps.get('board', 0))
                
                # Power
                power = jetson.power
                power_current = power.get('tot', {}).get('cur', 0) if power else 0
                power_avg = power.get('tot', {}).get('avg', 0) if power else 0
                
                # System info
                jetpack = jetson.board.get('jetpack', 'unknown')
                nvpmodel = jetson.nvpmodel.name if hasattr(jetson, 'nvpmodel') else 'unknown'
                uptime = int(jetson.uptime.total_seconds()) if hasattr(jetson, 'uptime') else 0
                
                with self._lock:
                    self._metrics = JetsonMetrics(
                        cpu_percent=round(cpu_percent, 1),
                        memory_percent=round(mem_percent, 1),
                        memory_used_mb=round(mem_used, 1),
                        memory_total_mb=round(mem_total, 1),
                        gpu_percent=round(gpu_percent, 1),
                        gpu_freq_mhz=int(gpu_freq),
                        temperature_cpu=round(temp_cpu, 1),
                        temperature_gpu=round(temp_gpu, 1),
                        temperature_board=round(temp_board, 1),
                        power_current_mw=int(power_current),
                        power_average_mw=int(power_avg),
                        jetpack_version=str(jetpack),
                        nvpmodel_mode=str(nvpmodel),
                        uptime_seconds=uptime
                    )
        except Exception as e:
            print(f"⚠️  jtop error: {e}")
            self._collect_mock_metrics()
    
    def _collect_mock_metrics(self):
        """Generate mock metrics for development/non-Jetson platforms"""
        import random
        
        with self._lock:
            self._metrics = JetsonMetrics(
                cpu_percent=random.uniform(20, 60),
                memory_percent=random.uniform(40, 70),
                memory_used_mb=random.uniform(3000, 5000),
                memory_total_mb=8192,
                gpu_percent=random.uniform(50, 80),
                gpu_freq_mhz=random.randint(600, 1100),
                temperature_cpu=random.uniform(40, 55),
                temperature_gpu=random.uniform(42, 58),
                temperature_board=random.uniform(38, 50),
                power_current_mw=random.randint(8000, 15000),
                power_average_mw=random.randint(10000, 12000),
                jetpack_version="5.1.2 (mock)",
                nvpmodel_mode="MAXN (mock)",
                uptime_seconds=int(time.time()) % 86400
            )
    
    def _collect_container_metrics(self):
        """Collect Docker container metrics"""
        try:
            result = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format',
                 '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                self._containers = self._get_mock_containers()
                return
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 3:
                    name = parts[0]
                    cpu = float(parts[1].replace('%', ''))
                    mem_str = parts[2].split('/')[0].strip()
                    
                    # Parse memory
                    if 'GiB' in mem_str:
                        mem = float(mem_str.replace('GiB', '').strip()) * 1024
                    elif 'MiB' in mem_str:
                        mem = float(mem_str.replace('MiB', '').strip())
                    else:
                        mem = 0
                    
                    containers.append(ContainerStatus(
                        name=name,
                        status='running',
                        uptime='',
                        cpu_percent=round(cpu, 1),
                        memory_mb=round(mem, 1)
                    ))
            
            with self._lock:
                self._containers = containers if containers else self._get_mock_containers()
        
        except Exception:
            with self._lock:
                self._containers = self._get_mock_containers()
    
    def _get_mock_containers(self) -> List[ContainerStatus]:
        """Return mock container data"""
        return [
            ContainerStatus(
                name="minimart-vision",
                status="running",
                uptime="2d 14h",
                cpu_percent=45.2,
                memory_mb=1024
            ),
            ContainerStatus(
                name="minimart-dashboard",
                status="running",
                uptime="2d 14h",
                cpu_percent=5.1,
                memory_mb=256
            ),
        ]
    
    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get current device metrics"""
        with self._lock:
            if self._metrics:
                return asdict(self._metrics)
            return None
    
    def get_containers(self) -> List[Dict[str, Any]]:
        """Get current container status"""
        with self._lock:
            return [asdict(c) for c in self._containers]
    
    def get_full_telemetry(self) -> Dict[str, Any]:
        """Get all telemetry data"""
        return {
            'device': self.get_metrics(),
            'containers': self.get_containers(),
            'is_jetson': self._is_jetson,
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
