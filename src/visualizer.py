"""
Dashboard Visualizer — Generates interactive HTML profiling dashboards.

Uses Jinja2 templates with Chart.js for rich visualizations.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ROCm Profiler Dashboard — {{ session_id }}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>
        :root {
            --bg: #0d1117;
            --card: #161b22;
            --border: #30363d;
            --text: #c9d1d9;
            --text-bright: #f0f6fc;
            --accent: #58a6ff;
            --green: #3fb950;
            --red: #f85149;
            --yellow: #d29922;
            --orange: #db6d28;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 20px;
        }
        .header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 30px;
        }
        .header h1 { color: var(--text-bright); font-size: 2em; }
        .header .subtitle { color: var(--text); margin-top: 8px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
        }
        .card h3 { color: var(--accent); margin-bottom: 12px; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; }
        .stat-value { font-size: 2.5em; font-weight: 700; color: var(--text-bright); }
        .stat-label { font-size: 0.85em; color: var(--text); margin-top: 4px; }
        .chart-container { position: relative; height: 300px; }
        .wide { grid-column: span 2; }
        .full { grid-column: 1 / -1; }
        .bottleneck {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
            margin: 2px;
        }
        .bottleneck.compute { background: rgba(88,166,255,0.2); color: var(--accent); }
        .bottleneck.memory { background: rgba(219,109,40,0.2); color: var(--orange); }
        .bottleneck.idle { background: rgba(248,81,73,0.2); color: var(--red); }
        .bottleneck.thermal { background: rgba(248,81,73,0.2); color: var(--red); }
        .bottleneck.power { background: rgba(210,153,34,0.2); color: var(--yellow); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border); }
        th { color: var(--accent); font-size: 0.85em; text-transform: uppercase; }
        td { font-size: 0.9em; }
        .recommendation { padding: 10px 15px; margin: 5px 0; background: rgba(63,185,80,0.1); border-left: 3px solid var(--green); border-radius: 4px; }
        .timestamp { color: var(--text); font-size: 0.8em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ ROCm Profiler Dashboard</h1>
        <div class="subtitle">Session: {{ session_id }} | GPU: {{ gpu_id }} | Duration: {{ duration }}s</div>
        <div class="timestamp">Generated: {{ timestamp }}</div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>GPU Utilization</h3>
            <div class="stat-value">{{ summary.gpu_utilization.average }}%</div>
            <div class="stat-label">Peak: {{ summary.gpu_utilization.peak }}% | Min: {{ summary.gpu_utilization.min }}%</div>
        </div>
        <div class="card">
            <h3>Memory Utilization</h3>
            <div class="stat-value">{{ summary.memory_utilization.average }}%</div>
            <div class="stat-label">Peak: {{ summary.memory_utilization.peak }}%</div>
        </div>
        <div class="card">
            <h3>Temperature</h3>
            <div class="stat-value">{{ summary.temperature.average }}°C</div>
            <div class="stat-label">Peak: {{ summary.temperature.peak }}°C</div>
        </div>
        <div class="card">
            <h3>Power</h3>
            <div class="stat-value">{{ summary.power.average_watts }}W</div>
            <div class="stat-label">Peak: {{ summary.power.peak_watts }}W</div>
        </div>
    </div>

    <div class="grid">
        <div class="card wide">
            <h3>GPU Utilization Timeline</h3>
            <div class="chart-container"><canvas id="utilChart"></canvas></div>
        </div>
        <div class="card wide">
            <h3>Power & Temperature Timeline</h3>
            <div class="chart-container"><canvas id="powerChart"></canvas></div>
        </div>
    </div>

    <div class="grid">
        <div class="card wide">
            <h3>Memory Usage</h3>
            <div class="chart-container"><canvas id="memChart"></canvas></div>
        </div>
    </div>

    {% if bottlenecks %}
    <div class="grid">
        <div class="card full">
            <h3>Bottleneck Analysis</h3>
            <div style="margin: 10px 0;">
                {% for b in bottlenecks %}
                <span class="bottleneck {{ b }}">{{ b }}</span>
                {% endfor %}
            </div>
            {% for rec in recommendations %}
            <div class="recommendation">{{ rec }}</div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <div class="grid">
        <div class="card full">
            <h3>Metric Statistics</h3>
            <table>
                <tr><th>Metric</th><th>Mean</th><th>Median</th><th>P90</th><th>P99</th><th>Max</th><th>Std Dev</th></tr>
                {% for metric, stats in summary_stats.items() %}
                <tr>
                    <td>{{ metric }}</td>
                    <td>{{ "%.2f"|format(stats.mean) }}</td>
                    <td>{{ "%.2f"|format(stats.median) }}</td>
                    <td>{{ "%.2f"|format(stats.p90) }}</td>
                    <td>{{ "%.2f"|format(stats.p99) }}</td>
                    <td>{{ "%.2f"|format(stats.max) }}</td>
                    <td>{{ "%.2f"|format(stats.std) }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>

    <script>
        const timestamps = {{ timestamps | safe }};
        const gpuData = {{ gpu_data | safe }};
        const memData = {{ mem_data | safe }};
        const tempData = {{ temp_data | safe }};
        const powerData = {{ power_data | safe }};

        const chartDefaults = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#c9d1d9' } } },
            scales: {
                x: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
                y: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }
            }
        };

        new Chart(document.getElementById('utilChart'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'GPU Utilization (%)',
                    data: gpuData,
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88,166,255,0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: { ...chartDefaults, scales: { ...chartDefaults.scales, y: { ...chartDefaults.scales.y, min: 0, max: 100 } } }
        });

        new Chart(document.getElementById('powerChart'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [
                    { label: 'Power (W)', data: powerData, borderColor: '#d29922', tension: 0.3, yAxisID: 'y' },
                    { label: 'Temp (°C)', data: tempData, borderColor: '#f85149', tension: 0.3, yAxisID: 'y1' }
                ]
            },
            options: {
                ...chartDefaults,
                scales: {
                    x: chartDefaults.scales.x,
                    y: { type: 'linear', position: 'left', ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
                    y1: { type: 'linear', position: 'right', ticks: { color: '#8b949e' }, grid: { drawOnChartArea: false } }
                }
            }
        });

        new Chart(document.getElementById('memChart'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Memory Utilization (%)',
                    data: memData,
                    borderColor: '#3fb950',
                    backgroundColor: 'rgba(63,185,80,0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: { ...chartDefaults, scales: { ...chartDefaults.scales, y: { ...chartDefaults.scales.y, min: 0, max: 100 } } }
        });
    </script>
</body>
</html>"""


class DashboardVisualizer:
    """Generates interactive HTML dashboards from profiling data."""

    def __init__(self, config: Dict[str, Any]):
        self.theme = config.get("theme", "dark")
        self.charts = config.get("charts", [
            "utilization_timeline", "power_timeline",
            "memory_usage", "bottleneck_summary",
        ])
        self.refresh_interval = config.get("refresh_interval_s", 0)

    def generate(self, results: Dict[str, Any], output_path: str = "dashboard.html"):
        """Generate HTML dashboard from profiling results.

        Args:
            results: Profiler results dictionary.
            output_path: Output HTML file path.
        """
        try:
            from jinja2 import Template
            template = Template(DASHBOARD_TEMPLATE)
        except ImportError:
            logger.warning("jinja2 not available, using string formatting")
            template = self._SimpleTemplate(DASHBOARD_TEMPLATE)

        raw_metrics = results.get("raw_metrics", [])
        analysis = results.get("analysis", {})
        summary = results.get("summary", {})

        # Prepare chart data
        timestamps = [f"{m.get('_elapsed', i):.1f}s" for i, m in enumerate(raw_metrics)]
        gpu_data = [round(m.get("gpu_use_percent", 0), 1) for m in raw_metrics]
        mem_data = [round(m.get("mem_use_percent", 0), 1) for m in raw_metrics]
        temp_data = [round(m.get("temperature", 0), 1) for m in raw_metrics]
        power_data = [round(m.get("power", 0), 1) for m in raw_metrics]

        # Limit data points for rendering
        max_points = 500
        if len(timestamps) > max_points:
            step = len(timestamps) // max_points
            timestamps = timestamps[::step]
            gpu_data = gpu_data[::step]
            mem_data = mem_data[::step]
            temp_data = temp_data[::step]
            power_data = power_data[::step]

        html = template.render(
            session_id=results.get("session_id", "unknown"),
            gpu_id=results.get("gpu_id", 0),
            duration=results.get("duration", 0),
            timestamp=results.get("timestamp", ""),
            summary=summary,
            summary_stats=analysis.get("summary_stats", {}),
            bottlenecks=summary.get("bottlenecks", []),
            recommendations=summary.get("recommendations", []),
            timestamps=json.dumps(timestamps),
            gpu_data=json.dumps(gpu_data),
            mem_data=json.dumps(mem_data),
            temp_data=json.dumps(temp_data),
            power_data=json.dumps(power_data),
        )

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html)
        logger.info(f"Dashboard saved to {output_path}")

    class _SimpleTemplate:
        """Fallback template renderer when jinja2 is unavailable."""
        def __init__(self, template_str):
            self.template = template_str

        def render(self, **kwargs):
            result = self.template
            for key, value in kwargs.items():
                result = result.replace("{{ " + key + " }}", str(value))
            return result
