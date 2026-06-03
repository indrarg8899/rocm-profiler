#!/usr/bin/env python3
"""
Compare two profiling runs side-by-side.

Usage:
    python scripts/compare_runs.py --run1 baseline.json --run2 optimized.json
"""

import argparse
import json
import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def load_run(path: str) -> Dict[str, Any]:
    """Load a profiling run from JSON."""
    with open(path) as f:
        return json.load(f)


def compare_runs(run1: Dict, run2: Dict) -> Dict[str, Any]:
    """Compare two profiling runs and compute deltas."""
    comparison = {
        "run1_session": run1.get("session_id", "unknown"),
        "run2_session": run2.get("session_id", "unknown"),
        "metrics": {},
        "bottleneck_changes": {},
    }

    # Compare summary metrics
    s1 = run1.get("summary", {})
    s2 = run2.get("summary", {})

    for metric_group in ["gpu_utilization", "memory_utilization", "temperature", "power"]:
        g1 = s1.get(metric_group, {})
        g2 = s2.get(metric_group, {})

        for sub_metric in ["average", "peak", "min", "max", "average_watts", "peak_watts"]:
            v1 = g1.get(sub_metric)
            v2 = g2.get(sub_metric)
            if v1 is not None and v2 is not None:
                delta = v2 - v1
                pct_change = (delta / v1 * 100) if v1 != 0 else 0
                comparison["metrics"][f"{metric_group}.{sub_metric}"] = {
                    "run1": round(v1, 2),
                    "run2": round(v2, 2),
                    "delta": round(delta, 2),
                    "pct_change": round(pct_change, 1),
                }

    # Compare bottlenecks
    b1 = set(s1.get("bottlenecks", []))
    b2 = set(s2.get("bottlenecks", []))
    comparison["bottleneck_changes"] = {
        "resolved": list(b1 - b2),
        "new": list(b2 - b1),
        "persistent": list(b1 & b2),
    }

    return comparison


def print_comparison(comparison: Dict):
    """Print comparison results to terminal."""
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        console.print(f"\n[bold cyan]Run Comparison[/bold cyan]")
        console.print(f"Baseline: {comparison['run1_session']}")
        console.print(f"Optimized: {comparison['run2_session']}\n")

        table = Table(title="Metric Comparison")
        table.add_column("Metric", style="cyan")
        table.add_column("Baseline", justify="right")
        table.add_column("Optimized", justify="right")
        table.add_column("Change", justify="right")
        table.add_column("Δ%", justify="right")

        for metric, data in comparison["metrics"].items():
            color = "green" if data["pct_change"] > 0 else "red" if data["pct_change"] < 0 else "white"
            table.add_row(
                metric,
                f"{data['run1']}",
                f"{data['run2']}",
                f"[{color}]{data['delta']:+.2f}[/{color}]",
                f"[{color}]{data['pct_change']:+.1f}%[/{color}]",
            )

        console.print(table)

        # Bottleneck changes
        bc = comparison["bottleneck_changes"]
        if bc["resolved"]:
            console.print("\n[green]✓ Resolved bottlenecks:[/green]")
            for b in bc["resolved"]:
                console.print(f"  - {b}")

        if bc["new"]:
            console.print("\n[red]✗ New bottlenecks:[/red]")
            for b in bc["new"]:
                console.print(f"  + {b}")

        if bc["persistent"]:
            console.print("\n[yellow]~ Persistent bottlenecks:[/yellow]")
            for b in bc["persistent"]:
                console.print(f"  ~ {b}")

        console.print()

    except ImportError:
        print("\n=== Run Comparison ===")
        for metric, data in comparison["metrics"].items():
            print(f"{metric}: {data['run1']} -> {data['run2']} ({data['pct_change']:+.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Compare two ROCm Profiler runs")
    parser.add_argument("--run1", type=str, required=True, help="Baseline run JSON")
    parser.add_argument("--run2", type=str, required=True, help="Optimized run JSON")
    parser.add_argument("--output", type=str, default=None, help="Save comparison to JSON")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    run1 = load_run(args.run1)
    run2 = load_run(args.run2)

    comparison = compare_runs(run1, run2)
    print_comparison(comparison)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(comparison, f, indent=2)
        print(f"Comparison saved to {args.output}")


if __name__ == "__main__":
    main()
