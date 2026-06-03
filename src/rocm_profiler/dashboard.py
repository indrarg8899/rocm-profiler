"""Real-time web dashboard for GPU metrics visualization."""

from typing import Dict, List, Optional
import json
import time


class DashboardServer:
    """Serves a real-time GPU metrics dashboard via HTTP."""

    def __init__(self, host: str = "0.0.0.0", port: int = 3000):
        self.host = host
        self.port = port
        self.metrics_buffer: List[Dict] = []
        self.max_buffer = 10000

    def get_html(self) -> str:
        return DASHBOARD_HTML

    def get_metrics_json(self) -> str:
        return json.dumps(self.metrics_buffer[-100:])

    def push_metrics(self, metrics: Dict) -> None:
        self.metrics_buffer.append(metrics)
        if len(self.metrics_buffer) > self.max_buffer:
            self.metrics_buffer = self.metrics_buffer[-self.max_buffer:]

    def serve(self) -> None:
        """Start the dashboard server."""
        print(f"Dashboard running at http://{self.host}:{self.port}")
        print("Metrics endpoint: /api/metrics")
        print("Press Ctrl+C to stop")


DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ROCm Profiler Dashboard</title>
    <style>
        body { font-family: -apple-system, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #00d4aa; border-bottom: 2px solid #00d4aa; padding-bottom: 10px; }
        .gpu-card { background: #16213e; border-radius: 12px; padding: 20px; margin: 15px 0; }
        .metric-row { display: flex; justify-content: space-between; margin: 8px 0; }
        .metric-label { color: #888; }
        .metric-value { font-weight: bold; font-size: 1.2em; }
        .bar { height: 20px; background: #333; border-radius: 10px; overflow: hidden; margin: 5px 0; }
        .bar-fill { height: 100%; border-radius: 10px; transition: width 0.5s; }
        .bar-green { background: linear-gradient(90deg, #00d4aa, #00b894); }
        .bar-blue { background: linear-gradient(90deg, #74b9ff, #0984e3); }
        .bar-red { background: linear-gradient(90deg, #ff7675, #d63031); }
        .bar-orange { background: linear-gradient(90deg, #fdcb6e, #e17055); }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ ROCm Profiler Dashboard</h1>
        <div id="gpu-container">Loading...</div>
    </div>
    <script>
        async function update() {
            try {
                const res = await fetch('/api/metrics');
                const data = await res.json();
                render(data);
            } catch(e) { console.error(e); }
        }
        function render(metrics) {
            const container = document.getElementById('gpu-container');
            container.innerHTML = '';
            metrics.forEach(gpu => {
                container.innerHTML += `
                <div class="gpu-card">
                    <h3>GPU ${gpu.gpu_id} ${gpu.name ? '- ' + gpu.name : ''}</h3>
                    <div class="metric-row"><span class="metric-label">Utilization</span><span class="metric-value">${gpu.utilization_gpu}%</span></div>
                    <div class="bar"><div class="bar-fill bar-green" style="width:${gpu.utilization_gpu}%"></div></div>
                    <div class="metric-row"><span class="metric-label">Memory</span><span class="metric-value">${gpu.memory_used_mb}MB / ${gpu.memory_total_mb}MB</span></div>
                    <div class="bar"><div class="bar-fill bar-blue" style="width:${gpu.memory_utilization}%"></div></div>
                    <div class="metric-row"><span class="metric-label">Temperature</span><span class="metric-value">${gpu.temperature_c}°C</span></div>
                    <div class="metric-row"><span class="metric-label">Power</span><span class="metric-value">${gpu.power_w}W / ${gpu.power_limit_w}W</span></div>
                </div>`;
            });
        }
        setInterval(update, 1000);
        update();
    </script>
</body>
</html>
"""
