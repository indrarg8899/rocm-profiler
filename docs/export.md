# Export Formats

## CSV Export

```bash
rocm-profiler monitor --export --output-dir ./output
```

Columns: `gpu_id, timestamp, utilization_gpu, memory_used_mb, temperature_c, power_w, ...`

## JSON Export

```json
{
  "export_time": "2024-01-15T10:30:00",
  "total_samples": 3600,
  "metrics": [...],
  "summary": {
    "gpu_utilization": {"mean": 78.5, "max": 100, "min": 12.3},
    "temperature": {"mean": 62.1, "max": 85.2, "min": 35.0},
    "power": {"mean": 312.5, "max": 450.0, "min": 50.0}
  }
}
```

## Integration with Pandas

```python
import pandas as pd
df = pd.read_csv("profiler_output/gpu_metrics.csv")
df.plot(x="timestamp", y=["utilization_gpu", "memory_utilization"])
```
