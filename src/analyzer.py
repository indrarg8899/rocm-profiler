"""
Performance Analyzer — Bottleneck detection and performance analysis.

Identifies compute-bound, memory-bound, and latency-bound patterns.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """Analyzes GPU metrics to detect bottlenecks and provide recommendations."""

    def __init__(self, config: Dict[str, Any]):
        self.bottleneck_detection = config.get("bottleneck_detection", True)
        self.roofline_analysis = config.get("roofline_analysis", False)
        self.occupancy_analysis = config.get("occupancy_analysis", True)
        self.memory_analysis = config.get("memory_analysis", True)
        self.threshold_percentile = config.get("threshold_percentile", 90)
        self.bw_limits = {
            "gfx90a": {"hbm_bw": 1600.0, "l2_bw": 600.0, "peak_flops": 38300},
            "gfx942": {"hbm_bw": 3200.0, "l2_bw": 1200.0, "peak_flops": 163400},
            "gfx1100": {"hbm_bw": 850.0, "l2_bw": 400.0, "peak_flops": 61400},
            "gfx1101": {"hbm_bw": 512.0, "l2_bw": 300.0, "peak_flops": 35200},
        }

    def analyze(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run full analysis on collected metrics.

        Args:
            metrics: List of metric snapshots from collector.

        Returns:
            Analysis results dictionary.
        """
        if not metrics:
            return {"error": "No metrics to analyze"}

        results = {
            "summary_stats": self._compute_stats(metrics),
            "trends": self._analyze_trends(metrics),
            "anomalies": self._detect_anomalies(metrics),
            "bottlenecks": [],
            "recommendations": [],
        }

        if self.bottleneck_detection:
            bottlenecks = self._detect_bottlenecks(metrics, results["summary_stats"])
            results["bottlenecks"] = bottlenecks["types"]
            results["bottleneck_details"] = bottlenecks["details"]
            results["recommendations"] = bottlenecks["recommendations"]

        if self.occupancy_analysis:
            results["occupancy"] = self._analyze_occupancy(metrics)

        if self.memory_analysis:
            results["memory"] = self._analyze_memory(metrics)

        if self.roofline_analysis:
            results["roofline"] = self._roofline_analysis(metrics)

        return results

    def _compute_stats(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Compute statistical summaries for all numeric fields."""
        stats = {}
        numeric_fields = [
            "gpu_use_percent", "mem_use_percent", "temperature",
            "power", "fan_speed", "clock_speed", "mem_used", "voltage",
        ]

        for field in numeric_fields:
            values = [m.get(field) for m in metrics if m.get(field) is not None]
            if not values:
                continue

            values.sort()
            n = len(values)
            stats[field] = {
                "mean": sum(values) / n,
                "median": values[n // 2],
                "min": values[0],
                "max": values[-1],
                "std": (sum((v - sum(values) / n) ** 2 for v in values) / n) ** 0.5,
                "p90": values[int(n * 0.9)],
                "p95": values[int(n * 0.95)],
                "p99": values[min(int(n * 0.99), n - 1)],
                "count": n,
            }

        return stats

    def _analyze_trends(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Analyze metric trends over time."""
        trends = {}
        for field in ["gpu_use_percent", "mem_use_percent", "temperature", "power"]:
            values = [m.get(field) for m in metrics if m.get(field) is not None]
            if len(values) < 3:
                continue

            first_half = values[: len(values) // 2]
            second_half = values[len(values) // 2:]
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)

            if avg_second > avg_first * 1.1:
                trends[field] = "increasing"
            elif avg_second < avg_first * 0.9:
                trends[field] = "decreasing"
            else:
                trends[field] = "stable"

        return trends

    def _detect_anomalies(self, metrics: List[Dict]) -> List[Dict[str, Any]]:
        """Detect anomalous metric values using z-score."""
        anomalies = []
        stats = self._compute_stats(metrics)

        for field, field_stats in stats.items():
            mean = field_stats["mean"]
            std = field_stats["std"]
            if std == 0:
                continue

            for i, m in enumerate(metrics):
                val = m.get(field)
                if val is None:
                    continue
                z_score = abs(val - mean) / std
                if z_score > 3.0:
                    anomalies.append({
                        "field": field,
                        "value": val,
                        "z_score": round(z_score, 2),
                        "expected_range": (round(mean - 2 * std, 2), round(mean + 2 * std, 2)),
                        "metric_index": i,
                    })

        return anomalies

    def _detect_bottlenecks(
        self, metrics: List[Dict], stats: Dict
    ) -> Dict[str, Any]:
        """Detect GPU bottlenecks: compute, memory, latency."""
        bottleneck_types = []
        details = []
        recommendations = []

        gpu_stats = stats.get("gpu_use_percent", {})
        mem_stats = stats.get("mem_use_percent", {})
        power_stats = stats.get("power", {})

        # Compute-bound detection
        if gpu_stats.get("p90", 0) > 90:
            bottleneck_types.append("compute")
            details.append({
                "type": "compute",
                "severity": "high" if gpu_stats.get("p99", 0) > 95 else "medium",
                "evidence": f"GPU utilization p90={gpu_stats['p90']:.1f}%",
            })
            recommendations.append(
                "GPU compute saturated — consider reducing kernel complexity or using mixed precision"
            )

        # Memory-bound detection
        if mem_stats.get("p90", 0) > 80:
            bottleneck_types.append("memory")
            details.append({
                "type": "memory",
                "severity": "high" if mem_stats.get("p99", 0) > 90 else "medium",
                "evidence": f"Memory utilization p90={mem_stats['p90']:.1f}%",
            })
            recommendations.append(
                "Memory bandwidth saturated — consider tiling, reducing data movement, or using channels_last"
            )

        # Idle detection
        if gpu_stats.get("mean", 0) < 20:
            bottleneck_types.append("idle")
            details.append({
                "type": "idle",
                "severity": "high",
                "evidence": f"GPU utilization mean={gpu_stats['mean']:.1f}% (mostly idle)",
            })
            recommendations.append(
                "GPU severely underutilized — check CPU-GPU pipeline, data loading, or async execution"
            )

        # Thermal throttling
        temp_stats = stats.get("temperature", {})
        if temp_stats.get("max", 0) > 95:
            bottleneck_types.append("thermal")
            details.append({
                "type": "thermal",
                "severity": "critical" if temp_stats["max"] > 100 else "high",
                "evidence": f"Peak temperature={temp_stats['max']:.1f}°C (throttle at ~100°C)",
            })
            recommendations.append(
                "Thermal throttling detected — improve cooling, reduce power limit, or lower workload"
            )

        # Power limit
        if power_stats.get("p90", 0) > 0:
            # Estimate if near TDP (rough heuristic: > 250W for consumer, > 350W for datacenter)
            if power_stats.get("mean", 0) > 300 and power_stats.get("std", 0) < 5:
                bottleneck_types.append("power")
                details.append({
                    "type": "power",
                    "severity": "medium",
                    "evidence": f"Sustained high power: mean={power_stats['mean']:.1f}W",
                })

        # Frequency stability
        clk_stats = stats.get("clock_speed", {})
        if clk_stats.get("std", 0) > clk_stats.get("mean", 1) * 0.15:
            bottleneck_types.append("clock_instability")
            details.append({
                "type": "clock_instability",
                "severity": "medium",
                "evidence": f"Clock std={clk_stats['std']:.1f} MHz (high variance)",
            })

        if not bottleneck_types:
            recommendations.append("No major bottlenecks detected — workload appears balanced")

        return {
            "types": bottleneck_types,
            "details": details,
            "recommendations": recommendations,
        }

    def _analyze_occupancy(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Analyze GPU occupancy characteristics."""
        occupancy_values = [m.get("occupancy") for m in metrics if m.get("occupancy") is not None]
        wavefront_values = [m.get("wavefronts") for m in metrics if m.get("wavefronts") is not None]

        result = {"available": bool(occupancy_values)}

        if occupancy_values:
            result["achieved"] = {
                "mean": sum(occupancy_values) / len(occupancy_values),
                "min": min(occupancy_values),
                "max": max(occupancy_values),
            }
            result["theoretical_max"] = 100.0
            result["efficiency"] = result["achieved"]["mean"] / 100.0

        if wavefront_values:
            result["wavefronts"] = {
                "mean": sum(wavefront_values) / len(wavefront_values),
                "peak": max(wavefront_values),
            }

        return result

    def _analyze_memory(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Analyze memory utilization patterns."""
        mem_used = [m.get("mem_used", 0) for m in metrics if m.get("mem_used")]
        mem_total = [m.get("mem_total", 0) for m in metrics if m.get("mem_total")]

        if not mem_used:
            return {"available": False}

        total = max(mem_total) if mem_total else 24576  # default 24GB
        result = {
            "available": True,
            "total_mb": total,
            "used": {
                "mean_mb": sum(mem_used) / len(mem_used),
                "peak_mb": max(mem_used),
                "min_mb": min(mem_used),
            },
            "utilization": {
                "mean_pct": (sum(mem_used) / len(mem_used)) / total * 100,
                "peak_pct": max(mem_used) / total * 100,
            },
            "headroom_mb": total - max(mem_used),
        }

        # Memory growth detection
        if len(mem_used) > 10:
            first_quarter = mem_used[: len(mem_used) // 4]
            last_quarter = mem_used[-len(mem_used) // 4:]
            avg_first = sum(first_quarter) / len(first_quarter)
            avg_last = sum(last_quarter) / len(last_quarter)
            growth = avg_last - avg_first
            result["memory_leak_indicator"] = growth > 100  # >100MB growth
            result["growth_mb"] = growth

        return result

    def _roofline_analysis(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Perform roofline model analysis."""
        return {
            "available": False,
            "reason": "Requires rocprof kernel-level data",
            "note": "Enable rocprof in config for roofline analysis",
        }

    def analyze_kernels(self, kernel_data: List[Dict]) -> Dict[str, Any]:
        """Analyze kernel-level profiling data from rocprof."""
        if not kernel_data:
            return {"available": False}

        total_time = sum(k.get("duration_us", 0) for k in kernel_data)
        sorted_kernels = sorted(kernel_data, key=lambda k: k.get("duration_us", 0), reverse=True)

        return {
            "available": True,
            "total_kernel_time_us": total_time,
            "kernel_count": len(kernel_data),
            "top_kernels": sorted_kernels[:10],
            "kernel_types": self._classify_kernels(sorted_kernels),
        }

    @staticmethod
    def _classify_kernels(kernels: List[Dict]) -> Dict[str, List]:
        """Classify kernels by type (compute, memory, etc)."""
        classifications = {"compute": [], "memory": [], "other": []}
        memory_keywords = ["copy", "memcpy", "memset", "read", "write", "load", "store", "transpose"]
        compute_keywords = ["gemm", "conv", "matmul", "reduce", "fft", "sort"]

        for kernel in kernels:
            name = kernel.get("name", "").lower()
            if any(kw in name for kw in memory_keywords):
                classifications["memory"].append(kernel.get("name", "unknown"))
            elif any(kw in name for kw in compute_keywords):
                classifications["compute"].append(kernel.get("name", "unknown"))
            else:
                classifications["other"].append(kernel.get("name", "unknown"))

        return classifications
