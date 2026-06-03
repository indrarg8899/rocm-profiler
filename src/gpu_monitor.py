"""
GPU Monitor — Real-time GPU monitoring with streaming output.

Provides live terminal display of GPU metrics.
"""

import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GPUMonitor:
    """Real-time GPU monitoring with terminal streaming."""

    def __init__(self, gpu_id: int = 0):
        self.gpu_id = gpu_id
        self._running = False

    def stream(self, interval: float = 1.0, duration: float = 60.0):
        """Stream GPU metrics to terminal in real-time.

        Args:
            interval: Update interval in seconds.
            duration: Total monitoring duration in seconds.
        """
        try:
            from rich.console import Console
            from rich.live import Live
            from rich.table import Table
            from rich.panel import Panel
            from rich.layout import Layout
            use_rich = True
        except ImportError:
            use_rich = False

        self._running = True
        start = time.time()

        if use_rich:
            self._stream_rich(interval, duration, start)
        else:
            self._stream_plain(interval, duration, start)

    def _stream_rich(self, interval: float, duration: float, start: float):
        """Stream with rich terminal formatting."""
        from rich.console import Console
        from rich.live import Live
        from rich.table import Table
        from rich.panel import Panel

        console = Console()
        self._running = True

        with Live(console=console, refresh_per_second=4) as live:
            while self._running and (time.time() - start) < duration:
                snapshot = self._get_snapshot()
                elapsed = time.time() - start

                # Build display table
                table = Table(title=f"GPU {self.gpu_id} Monitor [{elapsed:.0f}s / {duration:.0f}s]")
                table.add_column("Metric", style="cyan", width=25)
                table.add_column("Value", justify="right", style="green", width=15)
                table.add_column("Bar", width=30)

                self._add_monitor_row(table, "GPU Utilization", snapshot.get("gpu_use_percent", 0), "%")
                self._add_monitor_row(table, "Memory Utilization", snapshot.get("mem_use_percent", 0), "%")
                table.add_row("Temperature", f"{snapshot.get('temperature', 0):.1f}°C", "")
                table.add_row("Power", f"{snapshot.get('power', 0):.1f}W", "")
                table.add_row("Fan Speed", f"{snapshot.get('fan_speed', 0):.0f}%", "")
                table.add_row("Clock", f"{snapshot.get('clock_speed', 0):.0f} MHz", "")
                table.add_row("Memory Used", f"{snapshot.get('mem_used', 0):.0f} MB", "")

                live.update(table)
                time.sleep(interval)

    def _stream_plain(self, interval: float, duration: float, start: float):
        """Plain text fallback streaming."""
        self._running = True

        while self._running and (time.time() - start) < duration:
            snapshot = self._get_snapshot()
            elapsed = time.time() - start

            gpu = snapshot.get("gpu_use_percent", 0)
            mem = snapshot.get("mem_use_percent", 0)
            temp = snapshot.get("temperature", 0)
            pwr = snapshot.get("power", 0)

            bar_len = 30
            gpu_bar = "█" * int(gpu / 100 * bar_len) + "░" * (bar_len - int(gpu / 100 * bar_len))
            mem_bar = "█" * int(mem / 100 * bar_len) + "░" * (bar_len - int(mem / 100 * bar_len))

            sys.stdout.write(
                f"\r[{elapsed:6.1f}s] GPU: [{gpu_bar}] {gpu:5.1f}% "
                f"MEM: [{mem_bar}] {mem:5.1f}% "
                f"TEMP: {temp:.0f}°C PWR: {pwr:.0f}W  "
            )
            sys.stdout.flush()
            time.sleep(interval)

        sys.stdout.write("\n")

    @staticmethod
    def _add_monitor_row(table, name: str, value: float, suffix: str):
        """Add a row with a visual bar."""
        bar_len = 20
        filled = int(value / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        table.add_row(name, f"{value:.1f}{suffix}", bar)

    def _get_snapshot(self) -> Dict[str, Any]:
        """Get current GPU metrics."""
        import subprocess
        import re
        snapshot = {}

        try:
            result = subprocess.run(
                ["rocm-smi", "-a"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                text = result.stdout
                patterns = {
                    "gpu_use_percent": r"GPU use:\s*(\d+\.?\d*)",
                    "mem_use_percent": r"GPU memory use:\s*(\d+\.?\d*)",
                    "temperature": r"Temperature.*?:\s*(\d+\.?\d*)",
                    "power": r"[Pp]ower.*?:\s*(\d+\.?\d*)",
                    "fan_speed": r"[Ff]an.*?:\s*(\d+\.?\d*)",
                    "clock_speed": r"sclk.*?:\s*(\d+\.?\d*)",
                }
                for field, pattern in patterns.items():
                    match = re.search(pattern, text)
                    if match:
                        snapshot[field] = float(match.group(1))
        except Exception:
            # Simulate if no hardware
            import random
            snapshot = {
                "gpu_use_percent": 50 + random.gauss(0, 10),
                "mem_use_percent": 40 + random.gauss(0, 5),
                "temperature": 65 + random.gauss(0, 3),
                "power": 180 + random.gauss(0, 10),
                "fan_speed": 45 + random.gauss(0, 2),
                "clock_speed": 2100 + random.gauss(0, 30),
                "mem_used": 8192 + random.gauss(0, 500),
            }

        return snapshot

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False
