# ROCm Profiler — Quick Reference Card

## Commands

```bash
# Profile a process
python -m src.profiler --pid <PID> --duration 30

# Profile with dashboard
python -m src.profiler --pid <PID> --dashboard dashboard.html

# Real-time monitoring
python -m src.profiler --monitor

# Profile with tracing
python -m src.profiler --pid <PID> --config configs/tracing.yml

# Compare runs
python scripts/compare_runs.py --run1 base.json --run2 opt.json

# Profile a model
python scripts/profile_model.py --model resnet50 --framework pytorch
```

## Config Files

| Config | Interval | Tools | Use Case |
|--------|----------|-------|----------|
| `default.yml` | 100ms | rocm-smi | General profiling |
| `tracing.yml` | 50ms | rocm-smi + rocprof | Kernel analysis |

## Quick Bottleneck Check

```bash
python -m src.profiler --pid <PID> --duration 60 --format json
# Check summary.bottlenecks in output JSON
```
