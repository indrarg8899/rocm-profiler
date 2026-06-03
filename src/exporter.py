"""
Data Exporter — CSV/JSON export for profiling results.

Supports multiple output formats with metadata preservation.
"""

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DataExporter:
    """Exports profiling data to CSV, JSON, and Markdown formats."""

    def __init__(self, config: Dict[str, Any]):
        self.formats = config.get("formats", ["csv", "json"])
        self.include_metadata = config.get("include_metadata", True)
        self.include_kernel_details = config.get("include_kernel_details", True)

    def export(self, results: Dict[str, Any], output_path: str, fmt: str = "json"):
        """Export results to specified format.

        Args:
            results: Profiling results dictionary.
            output_path: Output file path.
            fmt: Output format: 'json', 'csv', or 'markdown'.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if fmt == "json":
            self._export_json(results, output)
        elif fmt == "csv":
            self._export_csv(results, output)
        elif fmt == "markdown":
            self._export_markdown(results, output)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        logger.info(f"Exported {fmt} to {output_path}")

    def _export_json(self, results: Dict[str, Any], path: Path):
        """Export to JSON with full metadata."""
        export_data = {
            "session_id": results.get("session_id"),
            "timestamp": results.get("timestamp"),
            "gpu_id": results.get("gpu_id"),
            "duration": results.get("duration"),
            "summary": results.get("summary"),
            "analysis": results.get("analysis"),
        }

        if self.include_metadata:
            export_data["config"] = results.get("config")
            export_data["collection_time"] = results.get("collection_time")

        if self.include_kernel_details:
            export_data["kernel_analysis"] = results.get("kernel_analysis")

        # Include raw metrics (potentially large)
        export_data["metrics"] = results.get("raw_metrics", [])

        with open(path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

    def _export_csv(self, results: Dict[str, Any], path: Path):
        """Export metrics to CSV."""
        metrics = results.get("raw_metrics", [])
        if not metrics:
            logger.warning("No metrics to export")
            return

        # Collect all field names
        all_fields = set()
        for m in metrics:
            all_fields.update(m.keys())
        fieldnames = sorted(all_fields)

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for m in metrics:
                writer.writerow(m)

    def _export_markdown(self, results: Dict[str, Any], path: Path):
        """Export summary as Markdown report."""
        summary = results.get("summary", {})
        analysis = results.get("analysis", {})
        session_id = results.get("session_id", "unknown")

        lines = [
            f"# ROCm Profiler Report",
            f"",
            f"**Session:** {session_id}",
            f"**Timestamp:** {results.get('timestamp', 'N/A')}",
            f"**GPU:** {results.get('gpu_id', 'N/A')}",
            f"**Duration:** {results.get('duration', 0)}s",
            f"",
            f"## GPU Utilization",
            f"",
        ]

        gpu = summary.get("gpu_utilization", {})
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Average | {gpu.get('average', 0)}% |")
        lines.append(f"| Peak | {gpu.get('peak', 0)}% |")
        lines.append(f"| Min | {gpu.get('min', 0)}% |")

        mem = summary.get("memory_utilization", {})
        lines.extend([
            f"",
            f"## Memory Utilization",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Average | {mem.get('average', 0)}% |",
            f"| Peak | {mem.get('peak', 0)}% |",
            f"",
        ])

        bottlenecks = summary.get("bottlenecks", [])
        if bottlenecks:
            lines.append("## Bottleneck Analysis")
            lines.append("")
            for b in bottlenecks:
                lines.append(f"- ⚠ **{b}**")
            lines.append("")

        recs = summary.get("recommendations", [])
        if recs:
            lines.append("## Recommendations")
            lines.append("")
            for r in recs:
                lines.append(f"- 💡 {r}")
            lines.append("")

        # Stats table
        stats = analysis.get("summary_stats", {})
        if stats:
            lines.append("## Detailed Statistics")
            lines.append("")
            lines.append("| Metric | Mean | Median | P90 | P99 | Max | Std |")
            lines.append("|--------|------|--------|-----|-----|-----|-----|")
            for metric, s in stats.items():
                lines.append(
                    f"| {metric} | {s.get('mean', 0):.2f} | {s.get('median', 0):.2f} | "
                    f"{s.get('p90', 0):.2f} | {s.get('p99', 0):.2f} | "
                    f"{s.get('max', 0):.2f} | {s.get('std', 0):.2f} |"
                )
            lines.append("")

        with open(path, "w") as f:
            f.write("\n".join(lines))
