"""
Tests for ROCm Profiler.

Tests collector, analyzer, visualizer, and exporter modules
without requiring actual ROCm hardware.
"""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.collector import MetricCollector
from src.analyzer import PerformanceAnalyzer
from src.visualizer import DashboardVisualizer
from src.exporter import DataExporter
from src.gpu_monitor import GPUMonitor
from src.kernel_analyzer import KernelAnalyzer


class TestMetricCollector(unittest.TestCase):
    """Test metric collection."""

    def test_simulated_collection(self):
        """Test simulated metrics when rocm-smi unavailable."""
        config = {"interval_ms": 50, "metrics": ["gpu_use_percent"]}
        collector = MetricCollector(config)
        metrics = collector.collect(duration=0.5, gpu_id=0)
        self.assertGreater(len(metrics), 0)
        self.assertIn("gpu_use_percent", metrics[0])

    def test_metric_fields(self):
        """Test that simulated metrics contain expected fields."""
        config = {"interval_ms": 50}
        collector = MetricCollector(config)
        metrics = collector.collect(duration=0.3, gpu_id=0)

        expected_fields = [
            "gpu_use_percent", "mem_use_percent", "temperature",
            "power", "fan_speed", "clock_speed",
        ]
        for field in expected_fields:
            self.assertIn(field, metrics[0], f"Missing field: {field}")

    def test_empty_config(self):
        """Test with minimal config."""
        collector = MetricCollector({})
        self.assertIsInstance(collector.interval_ms, int)

    def test_extract_numeric(self):
        """Test numeric extraction from strings."""
        self.assertEqual(MetricCollector._extract_numeric("42.5%"), 42.5)
        self.assertEqual(MetricCollector._extract_numeric(42), 42.0)
        self.assertIsNone(MetricCollector._extract_numeric("no numbers"))


class TestPerformanceAnalyzer(unittest.TestCase):
    """Test performance analysis."""

    def test_analyze_empty(self):
        """Test analysis with empty metrics."""
        analyzer = PerformanceAnalyzer({})
        result = analyzer.analyze([])
        self.assertIn("error", result)

    def test_analyze_basic(self):
        """Test analysis with sample metrics."""
        analyzer = PerformanceAnalyzer({})
        metrics = [
            {"gpu_use_percent": 80, "mem_use_percent": 50, "temperature": 70, "power": 200}
            for _ in range(10)
        ]
        result = analyzer.analyze(metrics)
        self.assertIn("summary_stats", result)
        self.assertIn("gpu_use_percent", result["summary_stats"])

    def test_bottleneck_detection(self):
        """Test compute bottleneck detection."""
        config = {"bottleneck_detection": True}
        analyzer = PerformanceAnalyzer(config)
        metrics = [
            {"gpu_use_percent": 95, "mem_use_percent": 30, "temperature": 75, "power": 250}
            for _ in range(20)
        ]
        result = analyzer.analyze(metrics)
        self.assertIn("compute", result.get("bottlenecks", []))

    def test_memory_bottleneck_detection(self):
        """Test memory bottleneck detection."""
        config = {"bottleneck_detection": True}
        analyzer = PerformanceAnalyzer(config)
        metrics = [
            {"gpu_use_percent": 40, "mem_use_percent": 90, "temperature": 75, "power": 200}
            for _ in range(20)
        ]
        result = analyzer.analyze(metrics)
        self.assertIn("memory", result.get("bottlenecks", []))

    def test_idle_detection(self):
        """Test idle GPU detection."""
        config = {"bottleneck_detection": True}
        analyzer = PerformanceAnalyzer(config)
        metrics = [
            {"gpu_use_percent": 10, "mem_use_percent": 5, "temperature": 45, "power": 50}
            for _ in range(20)
        ]
        result = analyzer.analyze(metrics)
        self.assertIn("idle", result.get("bottlenecks", []))

    def test_trend_analysis(self):
        """Test trend detection."""
        analyzer = PerformanceAnalyzer({})
        # Increasing trend
        metrics = [
            {"gpu_use_percent": 50 + i * 2, "mem_use_percent": 30, "temperature": 60}
            for i in range(20)
        ]
        result = analyzer.analyze(metrics)
        trends = result.get("trends", {})
        self.assertEqual(trends.get("gpu_use_percent"), "increasing")

    def test_anomaly_detection(self):
        """Test anomaly detection with outlier."""
        analyzer = PerformanceAnalyzer({})
        metrics = [
            {"gpu_use_percent": 50 + (i % 5), "mem_use_percent": 30, "temperature": 60}
            for i in range(20)
        ]
        # Inject outlier
        metrics[5]["gpu_use_percent"] = 200
        result = analyzer.analyze(metrics)
        anomalies = result.get("anomalies", [])
        self.assertTrue(any(a["field"] == "gpu_use_percent" for a in anomalies))


class TestDashboardVisualizer(unittest.TestCase):
    """Test HTML dashboard generation."""

    def test_generate_dashboard(self):
        """Test dashboard HTML generation."""
        visualizer = DashboardVisualizer({"theme": "dark"})
        results = {
            "session_id": "test_session",
            "gpu_id": 0,
            "duration": 10,
            "timestamp": "2024-01-01T00:00:00Z",
            "summary": {
                "gpu_utilization": {"average": 85.3, "peak": 97.1, "min": 12.4},
                "memory_utilization": {"average": 62.1, "peak": 78.3},
                "temperature": {"average": 72.4, "peak": 85.1},
                "power": {"average_watts": 180.5, "peak_watts": 250.0},
                "bottlenecks": ["compute"],
                "recommendations": ["Use mixed precision"],
            },
            "analysis": {"summary_stats": {}},
            "raw_metrics": [
                {"gpu_use_percent": 85, "mem_use_percent": 60, "temperature": 72,
                 "power": 180, "_elapsed": 0.1}
                for _ in range(100)
            ],
        }

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            output_path = f.name

        try:
            visualizer.generate(results, output_path)
            self.assertTrue(os.path.exists(output_path))
            content = Path(output_path).read_text()
            self.assertIn("ROCm Profiler Dashboard", content)
            self.assertIn("test_session", content)
        finally:
            os.unlink(output_path)


class TestDataExporter(unittest.TestCase):
    """Test data export."""

    def setUp(self):
        self.exporter = DataExporter({"formats": ["csv", "json"]})
        self.results = {
            "session_id": "test",
            "timestamp": "2024-01-01T00:00:00Z",
            "gpu_id": 0,
            "duration": 10,
            "summary": {"gpu_utilization": {"average": 85.3}},
            "analysis": {"summary_stats": {"gpu_use_percent": {"mean": 85.3}}},
            "raw_metrics": [
                {"gpu_use_percent": 85, "mem_use_percent": 60, "temperature": 72}
                for _ in range(10)
            ],
        }

    def test_json_export(self):
        """Test JSON export."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            self.exporter.export(self.results, path, fmt="json")
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data["session_id"], "test")
            self.assertEqual(len(data["metrics"]), 10)
        finally:
            os.unlink(path)

    def test_csv_export(self):
        """Test CSV export."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name

        try:
            self.exporter.export(self.results, path, fmt="csv")
            with open(path) as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 11)  # header + 10 rows
        finally:
            os.unlink(path)

    def test_markdown_export(self):
        """Test Markdown export."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            path = f.name

        try:
            self.exporter.export(self.results, path, fmt="markdown")
            content = Path(path).read_text()
            self.assertIn("ROCm Profiler Report", content)
            self.assertIn("85.3", content)
        finally:
            os.unlink(path)


class TestGPUMonitor(unittest.TestCase):
    """Test GPU monitor."""

    def test_stop(self):
        """Test monitor stop."""
        monitor = GPUMonitor(gpu_id=0)
        monitor._running = True
        monitor.stop()
        self.assertFalse(monitor._running)

    def test_get_snapshot(self):
        """Test getting a metric snapshot (may use simulated data)."""
        monitor = GPUMonitor(gpu_id=0)
        snapshot = monitor._get_snapshot()
        self.assertIsInstance(snapshot, dict)
        self.assertIn("gpu_use_percent", snapshot)


class TestKernelAnalyzer(unittest.TestCase):
    """Test kernel analyzer."""

    def test_missing_trace_file(self):
        """Test analysis with missing trace file."""
        analyzer = KernelAnalyzer({})
        result = analyzer.analyze("/nonexistent/path.csv")
        self.assertFalse(result.get("available", True))

    def test_empty_trace(self):
        """Test with empty trace file."""
        analyzer = KernelAnalyzer({})
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("KernelName,DurationNs,GridSize,WorkgroupSize\n")
            path = f.name

        try:
            result = analyzer.analyze(path)
            self.assertFalse(result.get("available", True))
        finally:
            os.unlink(path)

    def test_trace_with_kernels(self):
        """Test parsing kernel trace data."""
        analyzer = KernelAnalyzer({"roofline_analysis": False})
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("KernelName,DurationNs,GridSize,WorkgroupSize\n")
            f.write("conv2d_forward_64,12000000,1024,256\n")
            f.write("batch_norm_128,8000000,512,128\n")
            f.write("conv2d_forward_64,11000000,1024,256\n")
            path = f.name

        try:
            result = analyzer.analyze(path)
            self.assertTrue(result["available"])
            self.assertEqual(result["unique_kernels"], 2)
        finally:
            os.unlink(path)


class TestIntegration(unittest.TestCase):
    """Integration tests for full profiling pipeline."""

    def test_full_pipeline(self):
        """Test collector → analyzer → exporter pipeline."""
        # Collect
        config = {"interval_ms": 30}
        collector = MetricCollector(config)
        metrics = collector.collect(duration=0.5, gpu_id=0)
        self.assertGreater(len(metrics), 0)

        # Analyze
        analyzer = PerformanceAnalyzer({})
        analysis = analyzer.analyze(metrics)
        self.assertIn("summary_stats", analysis)

        # Export JSON
        results = {
            "session_id": "integration_test",
            "summary": {},
            "analysis": analysis,
            "raw_metrics": metrics,
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            exporter = DataExporter({})
            exporter.export(results, path, fmt="json")
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data["session_id"], "integration_test")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
