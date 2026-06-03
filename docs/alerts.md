# Alert Configuration

## Default Rules

| Rule | Metric | Threshold | Severity |
|---|---|---|---|
| High Temperature | temperature_c | > 85°C | WARNING |
| Critical Temperature | temperature_c | > 95°C | CRITICAL |
| High GPU Util | utilization_gpu | > 95% | INFO |
| Memory Pressure | memory_utilization | > 90% | WARNING |
| Critical Memory | memory_utilization | > 95% | CRITICAL |
| High Power | power_utilization | > 95% | WARNING |

## Custom Rules

```python
from rocm_profiler.alerts import AlertRule, AlertSeverity, AlertEngine

engine = AlertEngine()
engine.add_rule(AlertRule(
    name="Thermal Throttle Risk",
    metric="temperature_c",
    threshold=80.0,
    operator="gt",
    severity=AlertSeverity.WARNING,
    cooldown_seconds=120,
))

def my_handler(alert):
    print(f"ALERT: {alert.message}")

engine.add_handler(my_handler)
```

## Severity Levels

- **INFO**: Normal monitoring, no action needed
- **WARNING**: Should be investigated, may throttle
- **CRITICAL**: Immediate attention required, hardware risk
