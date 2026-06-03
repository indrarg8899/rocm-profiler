"""
Metric Collector — Collects GPU metrics from rocm-smi and rocprof.

Provides unified interface to ROCm profiling tools.
"""

import csv
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# rocm-smi field mappings
ROCMSMI_FIELDS = {
    "gpu_use_percent": ["GPU use", "GPU use (%)"],
    "mem_use_percent": ["GPU memory use", "GPU memory use (%)"],
    "mem_used": ["GPU memory used", "Used GPU Memory"],
    "mem_total": ["Total GPU memory", "Total GPU Memory"],
    "temperature": ["Temperature", "Temperature (Sensor edge)"],
    "power": ["Average Graphics Package Power", "Graphics Package Power"],
    "fan_speed": ["Fan speed", "Fan Speed (%)"],
    "clock_speed": ["sclk", "sclk clock speed"],
    "voltage": ["Voltage", "GPU Voltage"],
}


class MetricCollector:
    """Collects GPU metrics using rocm-smi and rocprof."""

    def __init__(self, config: Dict[str, Any]):
        self.interval_ms = config.get("interval_ms", 100)
        self.metrics = config.get("metrics", [
            "gpu_use_percent", "mem_use_percent", "mem_used",
            "temperature", "power", "fan_speed", "clock_speed",
        ])
        self.tools = config.get("tools", {"rocm_smi": True, "rocprof": False})
        self._check_tools()

    def _check_tools(self):
        """Verify available ROCm tools."""
        self.has_rocm_smi = self._command_exists("rocm-smi")
        self.has_rocprof = self._command_exists("rocprof")

        if self.tools.get("rocm_smi") and not self.has_rocm_smi:
            logger.warning("rocm-smi not found, will use mock data")
        if self.tools.get("rocprof") and not self.has_rocprof:
            logger.warning("rocprof not found, kernel tracing disabled")

    @staticmethod
    def _command_exists(cmd: str) -> bool:
        try:
            result = subprocess.run(
                ["which", cmd], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def collect(
        self,
        pid: Optional[int] = None,
        duration: float = 10.0,
        gpu_id: int = 0,
    ) -> List[Dict[str, Any]]:
        """Collect GPU metrics for the specified duration.

        Args:
            pid: Target process ID (informational).
            duration: Collection duration in seconds.
            gpu_id: GPU device ID.

        Returns:
            List of metric snapshots.
        """
        if not self.has_rocm_smi:
            logger.info("Using simulated metrics (rocm-smi unavailable)")
            return self._collect_simulated(duration, gpu_id)

        snapshots = []
        interval = self.interval_ms / 1000.0
        start = time.time()
        iteration = 0

        while (time.time() - start) < duration:
            try:
                snapshot = self._collect_rocm_smi(gpu_id, iteration)
                snapshot["_timestamp"] = time.time()
                snapshot["_elapsed"] = time.time() - start
                snapshots.append(snapshot)
            except Exception as e:
                logger.error(f"Collection error at iteration {iteration}: {e}")

            time.sleep(interval)
            iteration += 1

        logger.info(f"Collected {len(snapshots)} snapshots over {duration:.1f}s")
        return snapshots

    def _collect_rocm_smi(self, gpu_id: int, iteration: int) -> Dict[str, Any]:
        """Collect one snapshot from rocm-smi."""
        snapshot = {"gpu_id": gpu_id, "iteration": iteration}

        try:
            result = subprocess.run(
                ["rocm-smi", "--showuse", "--showmemuse", "--showtemp",
                 "--showpower", "--showfan", "--showclocks", "-a",
                 "--json"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                parsed = self._parse_rocm_smi_json(data, gpu_id)
                snapshot.update(parsed)
                return snapshot
        except (json.JSONDecodeError, subprocess.TimeoutExpired):
            pass

        # Fallback: plain text parsing
        try:
            result = subprocess.run(
                ["rocm-smi", "-a"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                parsed = self._parse_rocm_smi_text(result.stdout, gpu_id)
                snapshot.update(parsed)
        except subprocess.TimeoutExpired:
            pass

        return snapshot

    def _parse_rocm_smi_json(self, data: Dict, gpu_id: int) -> Dict[str, Any]:
        """Parse rocm-smi JSON output."""
        parsed = {}
        gpu_key = str(gpu_id)
        gpu_data = data.get(gpu_key, data.get("card0", data))

        if isinstance(gpu_data, dict):
            # Extract known fields
            for field, keys in ROCMSMI_FIELDS.items():
                for key in keys:
                    if key in gpu_data:
                        val = gpu_data[key]
                        parsed[field] = self._extract_numeric(val)
                        break

        return parsed

    def _parse_rocm_smi_text(self, text: str, gpu_id: int) -> Dict[str, Any]:
        """Parse rocm-smi plain text output."""
        parsed = {}
        patterns = {
            "gpu_use_percent": r"GPU use:\s*(\d+\.?\d*)",
            "mem_use_percent": r"GPU memory use:\s*(\d+\.?\d*)",
            "temperature": r"Temperature.*?:\s*(\d+\.?\d*)",
            "power": r"[Pp]ower.*?:\s*(\d+\.?\d*)",
            "fan_speed": r"[Ff]an.*?:\s*(\d+\.?\d*)",
            "clock_speed": r"[Cc]lock.*?sclk:\s*(\d+\.?\d*)",
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                parsed[field] = float(match.group(1))

        return parsed

    @staticmethod
    def _extract_numeric(val: Any) -> Optional[float]:
        """Extract numeric value from rocm-smi field."""
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            match = re.search(r"(\d+\.?\d*)", val)
            if match:
                return float(match.group(1))
        return None

    def _collect_simulated(self, duration: float, gpu_id: int) -> List[Dict[str, Any]]:
        """Generate simulated metrics for testing without GPU."""
        import random
        snapshots = []
        interval = self.interval_ms / 1000.0
        start = time.time()
        iteration = 0

        while (time.time() - start) < duration:
            t = time.time() - start
            base_util = 50 + 30 * (1 + __import__("math").sin(t * 0.5))
            snapshot = {
                "gpu_id": gpu_id,
                "iteration": iteration,
                "_timestamp": time.time(),
                "_elapsed": t,
                "gpu_use_percent": min(100, max(0, base_util + random.gauss(0, 5))),
                "mem_use_percent": min(100, max(0, 40 + random.gauss(0, 3))),
                "mem_used": 8192 + random.gauss(0, 512),
                "mem_total": 24576,
                "temperature": 65 + random.gauss(0, 3),
                "power": 180 + random.gauss(0, 15),
                "fan_speed": 45 + random.gauss(0, 2),
                "clock_speed": 2100 + random.gauss(0, 50),
                "voltage": 1.1 + random.gauss(0, 0.02),
            }
            snapshots.append(snapshot)
            time.sleep(interval)
            iteration += 1

        return snapshots

    def collect_rocprof_trace(
        self, command: List[str], gpu_id: int = 0, output: str = "/tmp/rocprof_trace.csv"
    ) -> str:
        """Run rocprof for kernel-level tracing.

        Args:
            command: Command to profile as list of args.
            gpu_id: GPU device ID.
            output: Output CSV path.

        Returns:
            Path to trace CSV file.
        """
        if not self.has_rocprof:
            raise RuntimeError("rocprof not available on this system")

        trace_args = [
            "rocprof",
            "--stats", "--hsa-trace",
            "--timestamp", "on",
            "-o", output,
            "--",
        ] + command

        logger.info(f"Running rocprof: {' '.join(trace_args)}")
        result = subprocess.run(trace_args, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            logger.error(f"rocprof failed: {result.stderr}")
            raise RuntimeError(f"rocprof failed with code {result.returncode}")

        logger.info(f"Trace saved to {output}")
        return output
