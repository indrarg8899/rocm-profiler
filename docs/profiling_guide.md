# ROCm Profiler — Advanced Profiling Guide

## Profiling Strategies

### Strategy 1: Utilization Profiling

Best for: Identifying underutilized GPU time.

```bash
# Long-running capture with default config
python -m src.profiler --pid <PID> --duration 300 --config configs/default.yml
```

**What to look for:**
- Low GPU utilization → CPU bottleneck or data loading issue
- Periodic dips → synchronization points or kernel launch gaps
- Steady low utilization → insufficient parallelism

### Strategy 2: Kernel Tracing

Best for: Per-kernel performance optimization.

```bash
# Requires rocprof (run as root)
sudo python -m src.profiler --pid <PID> --duration 60 --config configs/tracing.yml
```

**What to look for:**
- Kernel execution time distribution
- Memory-bound vs compute-bound kernels
- VGPR/SGPR usage affecting occupancy

### Strategy 3: Memory Profiling

Best for: Memory leak detection and bandwidth optimization.

```bash
# Extended monitoring to detect memory growth patterns
python -m src.profiler --pid <PID> --duration 600 --config configs/default.yml
```

**What to look for:**
- Monotonically increasing memory usage → possible leak
- Memory usage near capacity → OOM risk
- High memory utilization with low compute → memory-bound

## Analyzing Bottlenecks

### Compute-Bound

**Symptoms:**
- GPU utilization > 90%
- Low memory bandwidth utilization
- High FLOP count kernels

**Solutions:**
- Use mixed precision (FP16/BF16)
- Optimize arithmetic operations
- Reduce unnecessary computations

### Memory-Bound

**Symptoms:**
- GPU utilization < 70%
- Memory utilization > 80%
- Large data transfer kernels

**Solutions:**
- Use channels_last memory format
- Increase data reuse (tiling)
- Fuse memory operations
- Use shared memory / LDS

### Latency-Bound

**Symptoms:**
- Low GPU and memory utilization
- Many small kernels
- Frequent GPU-CPU synchronization

**Solutions:**
- Batch operations
- Use HIP stream for async execution
- Reduce CPU-GPU sync points
- Use persistent kernels

### Occupancy-Limited

**Symptoms:**
- Moderate GPU utilization
- High VGPR usage (> 64)
- Small grid sizes

**Solutions:**
- Reduce register pressure (fewer local variables)
- Use `__launch_bounds__` hints
- Increase block size for better CU utilization

## Run Comparison

Compare two profiling sessions to measure optimization impact:

```bash
python scripts/compare_runs.py \
  --run1 baseline.json \
  --run2 optimized.json \
  --output comparison.html
```

### Metrics Compared

| Metric | Description |
|--------|-------------|
| GPU Utilization | Mean, peak, and distribution change |
| Memory Bandwidth | Effective bandwidth difference |
| Kernel Times | Per-kernel execution time delta |
| Bottleneck Shift | Bottleneck category changes |
| Power Efficiency | Performance per watt improvement |

## Profiling PyTorch Models

```bash
# Profile a training run
python scripts/profile_model.py \
  --model resnet50 \
  --framework pytorch \
  --batch-size 64 \
  --iterations 100 \
  --config configs/tracing.yml
```

## Profiling Custom Kernels

```python
from src.profiler import ROCmProfiler

profiler = ROCmProfiler(config="configs/tracing.yml")

# Profile with kernel tracing
results = profiler.profile(pid=os.getpid(), duration=30)

# Access kernel data
for kernel in results["analysis"].get("bottleneck_kernels", []):
    print(f"{kernel['name']}: {kernel['issues']}")
```

## Best Practices

1. **Establish baseline** before optimization attempts
2. **Profile representative workloads** — don't micro-benchmark
3. **Collect enough samples** — at least 30 seconds for stable metrics
4. **Use tracing config** for kernel-level insights
5. **Run on dedicated hardware** — other processes affect results
6. **Consider environment** — power limits, thermal settings matter
7. **Iterate** — profile → optimize → verify → repeat
