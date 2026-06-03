"""
ROCm Profiler — Main profiling orchestrator.

Coordinates metric collection, analysis, visualization, and export.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import yaml

from src.collector import MetricCollector
from src.analyzer import PerformanceAnalyzer
from src.visualizer import DashboardVisualizer
from src.exporter import DataExporter
from src.gpu_monitor import GPUMonitor
from src.kernel_analyzer import KernelAnalyzer

logger = logging.getLogger(__name__)


class ROCmProfiler:
    """Main profiling orchestrator for AMD ROCm GPUs."""

    def __init__(self, config: str = "configs/default.yml", gpu_id: int = 0):
        self.config_path = config
        self.config = self._load_config(config)
        self.gpu_id = gpu_id
        self.collector = MetricCollector(self.config.get("collection", {}))
        self.analyzer = PerformanceAnalyzer(self.config.get("analysis", {}))
        self.visualizer = DashboardVisualizer(self.config.get("visualization", {}))
        self.exporter = DataExporter(self.config.get("export", {}))
        self.monitor = GPUMonitor(gpu_id)
        self.kernel_analyzer = KernelAnalyzer(self.config.get("analysis", {}))
        self.session_id = None
        self._results_cache = {}

    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        config_path = Path(path)
        if not config_path.exists():
            logger.warning(f"Config {path} not found, using defaults")
            return self._default_config()
        with open(config_path) as f:
            config = yaml.safe_load(f)
        return config or self._default_config()

    @staticmethod
    def _default_config() -> Dict[str, Any]:
        return {
            "collection": {
                "interval_ms": 100,
                "metrics": [
                    "gpu_use_percent", "mem_use_percent", "mem_used",
                    "temperature", "power", "fan_speed", "clock_speed",
                ],
                "tools": {"rocm_smi": True, "rocprof": False},
            },
            "analysis": {
                "bottleneck_detection": True,
                "roofline_analysis": False,
                "occupancy_analysis": True,
                "threshold_percentile": 90,
            },
            "visualization": {
                "format": "html",
                "theme": "dark",
                "charts": ["utilization_timeline"],
            },
            "export": {
                "formats": ["csv", "json"],
                "include_metadata": True,
            },
        }

    def profile(
        self,
        pid: Optional[int] = None,
        command: Optional[str] = None,
        duration: float = 10.0,
    ) -> Dict[str, Any]:
        """Run a complete profiling session.

        Args:
            pid: Process ID to attach to.
            command: Command string to launch and profile.
            duration: Profiling duration in seconds.

        Returns:
            Dictionary containing profiling results.
        """
        self.session_id = f"session_{int(time.time())}"
        logger.info(f"Starting profiling session {self.session_id}")
        logger.info(f"Duration: {duration}s, PID: {pid}, Command: {command}")

        # Collect metrics
        start_time = time.time()
        raw_metrics = self.collector.collect(
            pid=pid, duration=duration, gpu_id=self.gpu_id
        )
        collection_time = time.time() - start_time
        logger.info(f"Collected {len(raw_metrics)} metric snapshots in {collection_time:.2f}s")

        # Analyze results
        analysis = self.analyzer.analyze(raw_metrics)

        # Kernel analysis (if rocprof data available)
        kernel_data = None
        if self.config.get("collection", {}).get("tools", {}).get("rocprof"):
            kernel_data = self.kernel_analyzer.analyze(
                trace_path=f"/tmp/rocprof_{self.session_id}.csv"
            )

        results = {
            "session_id": self.session_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "config": self.config,
            "gpu_id": self.gpu_id,
            "pid": pid,
            "duration": duration,
            "collection_time": collection_time,
            "raw_metrics": raw_metrics,
            "analysis": analysis,
            "kernel_analysis": kernel_data,
            "summary": self._build_summary(raw_metrics, analysis),
        }

        self._results_cache[self.session_id] = results
        logger.info("Profiling session complete")
        return results

    def _build_summary(
        self, metrics: List[Dict], analysis: Dict
    ) -> Dict[str, Any]:
        """Build human-readable summary of profiling results."""
        if not metrics:
            return {"error": "No metrics collected"}

        gpu_util = [m.get("gpu_use_percent", 0) for m in metrics]
        mem_util = [m.get("mem_use_percent", 0) for m in metrics]
        temps = [m.get("temperature", 0) for m in metrics]
        power = [m.get("power", 0) for m in metrics]

        summary = {
            "gpu_utilization": {
                "average": round(sum(gpu_util) / len(gpu_util), 1),
                "peak": round(max(gpu_util), 1),
                "min": round(min(gpu_util), 1),
            },
            "memory_utilization": {
                "average": round(sum(mem_util) / len(mem_util), 1),
                "peak": round(max(mem_util), 1),
            },
            "temperature": {
                "average": round(sum(temps) / len(temps), 1),
                "peak": round(max(temps), 1),
            },
            "power": {
                "average_watts": round(sum(power) / len(power), 1),
                "peak_watts": round(max(power), 1),
            },
            "bottlenecks": analysis.get("bottlenecks", []),
            "recommendations": analysis.get("recommendations", []),
        }
        return summary

    def visualize(self, results: Dict[str, Any], output: str = "dashboard.html"):
        """Generate HTML dashboard from profiling results."""
        logger.info(f"Generating dashboard: {output}")
        self.visualizer.generate(results, output_path=output)

    def export(self, results: Dict[str, Any], format: str = "json", output: str = "results.json"):
        """Export profiling data."""
        logger.info(f"Exporting results to {output} (format={format})")
        self.exporter.export(results, output_path=output, fmt=format)

    def monitor_realtime(self, interval: float = 1.0, duration: float = 60.0):
        """Start real-time GPU monitoring to stdout."""
        self.monitor.stream(interval=interval, duration=duration)


@click.command()
@click.option("--pid", type=int, help="Process ID to profile")
@click.option("--command", type=str, help="Command to launch and profile")
@click.option("--config", type=str, default="configs/default.yml", help="Config YAML path")
@click.option("--duration", type=float, default=10.0, help="Profiling duration (seconds)")
@click.option("--gpu", type=int, default=0, help="GPU device ID")
@click.option("--output", type=str, default="results.json", help="Output file path")
@click.option("--format", type=str, default="json", help="Export format: json|csv")
@click.option("--dashboard", type=str, default=None, help="Generate HTML dashboard")
@click.option("--monitor", is_flag=True, help="Real-time monitoring mode")
@click.option("-v", "--verbose", is_flag=True, help="Verbose logging")
def main(pid, command, config, duration, gpu, output, format, dashboard, monitor, verbose):
    """ROCm Profiler — GPU profiling for AMD ROCm."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    profiler = ROCmProfiler(config=config, gpu_id=gpu)

    if monitor:
        profiler.monitor_realtime()
        return

    results = profiler.profile(pid=pid, command=command, duration=duration)

    # Export results
    profiler.export(results, format=format, output=output)

    # Generate dashboard if requested
    if dashboard:
        profiler.visualize(results, output=dashboard)

    # Print summary to terminal
    _print_terminal_summary(results["summary"])


def _print_terminal_summary(summary: Dict):
    """Pretty-print summary to terminal."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel

        console = Console()
        console.print()
        console.print(Panel.fit("[bold cyan]ROCm Profiler Session Report[/bold cyan]"))

        table = Table(show_header=True, header_style="bold green")
        table.add_column("Metric", style="cyan")
        table.add_column("Average", justify="right")
        table.add_column("Peak", justify="right")
        table.add_column("Min", justify="right")

        gpu = summary.get("gpu_utilization", {})
        mem = summary.get("memory_utilization", {})
        temp = summary.get("temperature", {})
        pwr = summary.get("power", {})

        table.add_row("GPU Utilization", f"{gpu.get('average', 0)}%", f"{gpu.get('peak', 0)}%", f"{gpu.get('min', 0)}%")
        table.add_row("Memory Utilization", f"{mem.get('average', 0)}%", f"{mem.get('peak', 0)}%", "—")
        table.add_row("Temperature", f"{temp.get('average', 0)}°C", f"{temp.get('peak', 0)}°C", "—")
        table.add_row("Power", f"{pwr.get('average_watts', 0)}W", f"{pwr.get('peak_watts', 0)}W", "—")

        console.print(table)

        bottlenecks = summary.get("bottlenecks", [])
        if bottlenecks:
            console.print("\n[bold yellow]⚠ Bottlenecks:[/bold yellow]")
            for b in bottlenecks:
                console.print(f"  • {b}")

        recs = summary.get("recommendations", [])
        if recs:
            console.print("\n[bold green]💡 Recommendations:[/bold green]")
            for r in recs:
                console.print(f"  • {r}")

        console.print()
    except ImportError:
        # Fallback without rich
        print("\n=== ROCm Profiler Session Report ===")
        gpu = summary.get("gpu_utilization", {})
        print(f"GPU Util: avg={gpu.get('average', 0)}% peak={gpu.get('peak', 0)}%")
        mem = summary.get("memory_utilization", {})
        print(f"Mem Util: avg={mem.get('average', 0)}% peak={mem.get('peak', 0)}%")


if __name__ == "__main__":
    main()
