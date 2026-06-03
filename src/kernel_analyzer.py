"""
Kernel Analyzer — Kernel-level Compute Unit analysis.

Analyzes rocprof trace data for per-kernel performance metrics.
"""

import csv
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class KernelAnalyzer:
    """Analyzes kernel-level performance from rocprof traces."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.roofline = config.get("roofline_analysis", False)
        self.occupancy_threshold = config.get("occupancy_threshold", 80)

    def analyze(self, trace_path: str) -> Dict[str, Any]:
        """Analyze kernel trace data from rocprof.

        Args:
            trace_path: Path to rocprof CSV output.

        Returns:
            Kernel analysis results.
        """
        if not os.path.exists(trace_path):
            logger.warning(f"Trace file not found: {trace_path}")
            return {"available": False, "reason": "trace file not found"}

        kernels = self._parse_trace(trace_path)
        if not kernels:
            return {"available": False, "reason": "no kernels found in trace"}

        analysis = {
            "available": True,
            "kernel_count": len(kernels),
            "total_time_us": sum(k["duration_us"] for k in kernels),
            "unique_kernels": len(set(k["name"] for k in kernels)),
            "kernels": self._aggregate_kernels(kernels),
            "top_by_time": sorted(kernels, key=lambda k: k["duration_us"], reverse=True)[:20],
            "timeline": self._build_timeline(kernels),
            "cu_analysis": self._analyze_cu_usage(kernels),
            "memory_analysis": self._analyze_kernel_memory(kernels),
        }

        if self.roofline:
            analysis["roofline"] = self._compute_roofline(kernels)

        analysis["bottleneck_kernels"] = self._identify_bottleneck_kernels(analysis["kernels"])

        return analysis

    def _parse_trace(self, path: str) -> List[Dict[str, Any]]:
        """Parse rocprof CSV trace file."""
        kernels = []

        try:
            with open(path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    kernel = self._parse_kernel_row(row)
                    if kernel:
                        kernels.append(kernel)
        except Exception as e:
            logger.error(f"Failed to parse trace: {e}")

        return kernels

    def _parse_kernel_row(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Parse a single kernel row from rocprof output."""
        kernel = {}

        # Common rocprof column names
        name_fields = ["KernelName", "kernel_name", "Name", "name"]
        dur_fields = ["Duration", "duration", "DurationNs", "EndNs", "AvgDuration"]
        grid_fields = ["GridSize", "grid_size", "Grid"]
        wg_fields = ["WorkgroupSize", "workgroup_size", "WorkGroup"]
        lds_fields = ["LDSPerWorkgroup", "lds_per_workgroup"]
        vgpr_fields = ["VGPRs", "vgprs", "NumVGPRs"]
        sgpr_fields = ["SGPRs", "sgprs", "NumSGPRs"]

        # Extract kernel name
        for field in name_fields:
            if field in row and row[field]:
                kernel["name"] = row[field].strip()
                break

        if "name" not in kernel:
            return None

        # Extract duration
        for field in dur_fields:
            if field in row and row[field]:
                try:
                    val = float(row[field])
                    # Convert ns to us if needed
                    kernel["duration_us"] = val / 1000 if val > 1e6 else val
                    break
                except ValueError:
                    continue

        if "duration_us" not in kernel:
            kernel["duration_us"] = 0

        # Extract grid/workgroup
        for field in grid_fields:
            if field in row and row[field]:
                try:
                    kernel["grid_size"] = int(float(row[field]))
                    break
                except ValueError:
                    continue

        for field in wg_fields:
            if field in row and row[field]:
                try:
                    kernel["workgroup_size"] = int(float(row[field]))
                    break
                except ValueError:
                    continue

        # Register usage
        for field, key in [(vgpr_fields, "vgprs"), (sgpr_fields, "sgprs")]:
            for f in field:
                if f in row and row[f]:
                    try:
                        kernel[key] = int(float(row[f]))
                        break
                    except ValueError:
                        continue

        return kernel

    def _aggregate_kernels(self, kernels: List[Dict]) -> List[Dict[str, Any]]:
        """Aggregate kernel stats by kernel name."""
        groups = defaultdict(list)
        for k in kernels:
            groups[k["name"]].append(k)

        aggregated = []
        for name, group in groups.items():
            durations = [k["duration_us"] for k in group]
            aggregated.append({
                "name": name,
                "calls": len(group),
                "total_us": sum(durations),
                "mean_us": sum(durations) / len(durations),
                "min_us": min(durations),
                "max_us": max(durations),
                "std_us": (sum((d - sum(durations)/len(durations))**2 for d in durations) / len(durations))**0.5,
                "grid_size": group[0].get("grid_size"),
                "workgroup_size": group[0].get("workgroup_size"),
                "vgprs": group[0].get("vgprs"),
                "sgprs": group[0].get("sgprs"),
                "pct_of_total": 0,  # filled below
            })

        total_time = sum(a["total_us"] for a in aggregated) or 1
        for a in aggregated:
            a["pct_of_total"] = round(a["total_us"] / total_time * 100, 2)

        return sorted(aggregated, key=lambda a: a["total_us"], reverse=True)

    def _build_timeline(self, kernels: List[Dict]) -> List[Dict]:
        """Build execution timeline for visualization."""
        timeline = []
        cumulative = 0
        for k in kernels:
            timeline.append({
                "name": k["name"],
                "start_us": cumulative,
                "duration_us": k["duration_us"],
                "end_us": cumulative + k["duration_us"],
            })
            cumulative += k["duration_us"]
        return timeline

    def _analyze_cu_usage(self, kernels: List[Dict]) -> Dict[str, Any]:
        """Analyze Compute Unit utilization patterns."""
        if not kernels:
            return {"available": False}

        # Estimate CU usage from grid/workgroup sizes
        cu_data = []
        for k in kernels:
            grid = k.get("grid_size", 0)
            wg = k.get("workgroup_size", 64)
            if grid and wg:
                num_wgs = max(1, grid // wg)
                cu_data.append({
                    "name": k["name"],
                    "workgroups": num_wgs,
                    "estimated_cu_occupancy": min(100, num_wgs / 104 * 100),  # 104 CUs on MI250
                })

        if not cu_data:
            return {"available": False, "reason": "no grid/workgroup data"}

        avg_occupancy = sum(d["estimated_cu_occupancy"] for d in cu_data) / len(cu_data)

        return {
            "available": True,
            "avg_cu_occupancy": round(avg_occupancy, 1),
            "low_occupancy_kernels": [
                d["name"] for d in cu_data
                if d["estimated_cu_occupancy"] < self.occupancy_threshold
            ],
        }

    def _analyze_kernel_memory(self, kernels: List[Dict]) -> Dict[str, Any]:
        """Analyze memory patterns per kernel."""
        if not kernels:
            return {"available": False}

        vgpr_usage = [k["vgprs"] for k in kernels if k.get("vgprs")]
        sgpr_usage = [k["sgprs"] for k in kernels if k.get("sgprs")]

        result = {"available": True}

        if vgpr_usage:
            result["vgpr"] = {
                "mean": sum(vgpr_usage) / len(vgpr_usage),
                "max": max(vgpr_usage),
                "high_usage_kernels": [
                    k["name"] for k in kernels
                    if k.get("vgprs", 0) > 64
                ],
            }

        if sgpr_usage:
            result["sgpr"] = {
                "mean": sum(sgpr_usage) / len(sgpr_usage),
                "max": max(sgpr_usage),
            }

        return result

    def _compute_roofline(self, kernels: List[Dict]) -> Dict[str, Any]:
        """Compute roofline model data points."""
        return {
            "available": True,
            "note": "Roofline analysis requires FLOP count from rocprof --stats",
            "data_points": [],
        }

    def _identify_bottleneck_kernels(self, aggregated: List[Dict]) -> List[Dict]:
        """Identify kernels that are potential bottlenecks."""
        bottlenecks = []
        total_time = sum(a["total_us"] for a in aggregated) or 1

        for kernel in aggregated:
            issues = []
            pct = kernel["pct_of_total"]

            if pct > 20:
                issues.append(f"dominates execution time ({pct}%)")
            if kernel.get("vgprs", 0) > 64:
                issues.append(f"high VGPR usage ({kernel['vgprs']}) limits occupancy")
            if kernel.get("std_us", 0) > kernel.get("mean_us", 1) * 0.5:
                issues.append("high runtime variance")

            if issues:
                bottlenecks.append({
                    "name": kernel["name"],
                    "pct_of_total": pct,
                    "issues": issues,
                })

        return bottlenecks
