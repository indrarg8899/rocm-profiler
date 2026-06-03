"""CSV and JSON export for profiling data."""

import csv
import json
import os
from typing import Dict, List
from datetime import datetime


class MetricsExporter:
    """Export GPU metrics to CSV and JSON formats."""

    def __init__(self, output_dir: str = "./profiler_output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_csv(
        self,
        metrics_history: List[Dict],
        filename: str = "gpu_metrics",
    ) -> str:
        """Export metrics to CSV file."""
        if not metrics_history:
            raise ValueError("No metrics to export")

        path = os.path.join(self.output_dir, f"{filename}.csv")
        fieldnames = list(metrics_history[0].keys())

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(metrics_history)

        print(f"Exported {len(metrics_history)} rows to {path}")
        return path

    def export_json(
        self,
        metrics_history: List[Dict],
        filename: str = "gpu_metrics",
    ) -> str:
        """Export metrics to JSON file."""
        path = os.path.join(self.output_dir, f"{filename}.json")

        data = {
            "export_time": datetime.now().isoformat(),
            "total_samples": len(metrics_history),
            "metrics": metrics_history,
            "summary": self._compute_summary(metrics_history),
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        print(f"Exported {len(metrics_history)} samples to {path}")
        return path

    def _compute_summary(self, metrics: List[Dict]) -> Dict:
        if not metrics:
            return {}

        gpu_utils = [m.get("utilization_gpu", 0) for m in metrics]
        temps = [m.get("temperature_c", 0) for m in metrics]
        powers = [m.get("power_w", 0) for m in metrics]
        mem_utils = [m.get("memory_utilization", 0) for m in metrics]

        return {
            "gpu_utilization": {
                "mean": sum(gpu_utils) / len(gpu_utils),
                "max": max(gpu_utils),
                "min": min(gpu_utils),
            },
            "temperature": {
                "mean": sum(temps) / len(temps),
                "max": max(temps),
                "min": min(temps),
            },
            "power": {
                "mean": sum(powers) / len(powers),
                "max": max(powers),
                "min": min(powers),
            },
            "memory_utilization": {
                "mean": sum(mem_utils) / len(mem_utils),
                "max": max(mem_utils),
                "min": min(mem_utils),
            },
            "duration_seconds": (
                metrics[-1].get("timestamp", 0) - metrics[0].get("timestamp", 0)
            ),
        }
