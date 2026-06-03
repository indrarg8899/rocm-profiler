"""GPU metrics collector using rocm-smi and sysfs."""

import os
import subprocess
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class GPUMetrics:
    gpu_id: int
    timestamp: float
    name: str = ""
    utilization_gpu: float = 0.0
    utilization_memory: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    temperature_c: float = 0.0
    power_w: float = 0.0
    power_limit_w: float = 0.0
    clock_sm_mhz: float = 0.0
    clock_mem_mhz: float = 0.0
    fan_speed: float = 0.0
    pcie_gen: int = 0
    pcie_width: int = 0

    @property
    def memory_utilization(self) -> float:
        if self.memory_total_mb > 0:
            return self.memory_used_mb / self.memory_total_mb
        return 0.0

    @property
    def power_utilization(self) -> float:
        if self.power_limit_w > 0:
            return self.power_w / self.power_limit_w
        return 0.0

    def to_dict(self) -> Dict:
        return {
            "gpu_id": self.gpu_id,
            "timestamp": self.timestamp,
            "name": self.name,
            "utilization_gpu": round(self.utilization_gpu, 1),
            "utilization_memory": round(self.utilization_memory, 1),
            "memory_used_mb": round(self.memory_used_mb, 1),
            "memory_total_mb": round(self.memory_total_mb, 1),
            "memory_utilization": round(self.memory_utilization * 100, 1),
            "temperature_c": round(self.temperature_c, 1),
            "power_w": round(self.power_w, 1),
            "power_limit_w": round(self.power_limit_w, 1),
            "power_utilization": round(self.power_utilization * 100, 1),
            "clock_sm_mhz": round(self.clock_sm_mhz, 0),
            "clock_mem_mhz": round(self.clock_mem_mhz, 0),
        }


class MetricsCollector:
    """Collects GPU metrics from rocm-smi and sysfs."""

    def __init__(self, use_rocm_smi: bool = True, sysfs_path: str = "/sys/class/drm"):
        self.use_rocm_smi = use_rocm_smi
        self.sysfs_path = sysfs_path

    def collect_all(self) -> List[GPUMetrics]:
        """Collect metrics for all GPUs."""
        num_gpus = self._get_gpu_count()
        return [self.collect(gpu_id) for gpu_id in range(num_gpus)]

    def collect(self, gpu_id: int) -> GPUMetrics:
        """Collect metrics for a single GPU."""
        metrics = GPUMetrics(gpu_id=gpu_id, timestamp=time.time())

        if self.use_rocm_smi:
            self._collect_rocm_smi(metrics)
        else:
            self._collect_sysfs(metrics)

        return metrics

    def _get_gpu_count(self) -> int:
        if self.use_rocm_smi:
            return self._query_rocm_smi("--showid", "--csv")["gpu_count"]
        return self._count_sysfs_devices()

    def _collect_rocm_smi(self, metrics: GPUMetrics) -> None:
        try:
            result = self._query_rocm_smi("--showuse", "--showmemuse", "--showtemp", "--showpower", "--csv")
            if metrics.gpu_id in result["data"]:
                d = result["data"][metrics.gpu_id]
                metrics.utilization_gpu = float(d.get("gpu_use", 0).strip("%"))
                metrics.utilization_memory = float(d.get("mem_use", 0).strip("%"))
                metrics.temperature_c = float(d.get("temp", 0).replace("C", ""))
                metrics.power_w = float(d.get("power", 0).replace("W", ""))
        except Exception:
            pass

    def _collect_sysfs(self, metrics: GPUMetrics) -> None:
        device_path = os.path.join(self.sysfs_path, f"card{metrics.gpu_id}")
        for key, attr in [
            ("gpu_util", "pp_dpm_sclk"),
            ("mem_util", "pp_dpm_mclk"),
            ("temperature", "temp1_input"),
        ]:
            fpath = os.path.join(device_path, "device/hwmon/hwmon0", attr)
            if os.path.exists(fpath):
                try:
                    with open(fpath) as f:
                        val = f.read().strip()
                        setattr(metrics, key, float(val))
                except (ValueError, IOError):
                    pass

    def _query_rocm_smi(self, *args) -> Dict:
        cmd = ["rocm-smi"] + list(args)
        try:
            output = subprocess.check_output(cmd, timeout=5, text=True)
            return {"data": {}, "gpu_count": output.count("GPU") // max(1, output.count("\n")), "raw": output}
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {"data": {}, "gpu_count": 0, "raw": ""}

    def _count_sysfs_devices(self) -> int:
        count = 0
        i = 0
        while os.path.exists(os.path.join(self.sysfs_path, f"card{i}")):
            count += 1
            i += 1
        return count
