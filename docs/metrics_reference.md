# ROCm Metrics Reference

## GPU Utilization Metrics

| Metric | Source | Description | Unit |
|--------|--------|-------------|------|
| `gpu_use_percent` | rocm-smi | GPU engine utilization | % |
| `mem_use_percent` | rocm-smi | GPU memory utilization | % |
| `mem_used` | rocm-smi | GPU memory used | MB |
| `mem_total` | rocm-smi | Total GPU memory | MB |

## Hardware Sensors

| Metric | Source | Description | Unit |
|--------|--------|-------------|------|
| `temperature` | rocm-smi | GPU edge temperature | °C |
| `power` | rocm-smi | GPU package power draw | W |
| `fan_speed` | rocm-smi | Fan speed percentage | % |
| `clock_speed` | rocm-smi | GPU shader clock | MHz |
| `voltage` | rocm-smi | GPU core voltage | V |

## Kernel Metrics (rocprof)

| Metric | Source | Description | Unit |
|--------|--------|-------------|------|
| `wavefronts` | rocprof | Active wavefronts per CU | count |
| `occupancy` | rocprof | CU occupancy percentage | % |
| `vgprs` | rocprof | Vector registers per workitem | count |
| `sgprs` | rocprof | Scalar registers per workitem | count |
| `lds` | rocprof | Local Data Share usage | bytes |
| `duration_us` | rocprof | Kernel execution time | μs |
| `grid_size` | rocprof | Number of workgroups | count |
| `workgroup_size` | rocprof | Workgroup dimensions | count |
| `flops` | rocprof | Floating point operations | count |
| `mem_bytes_read` | rocprof | Global memory bytes read | bytes |
| `mem_bytes_write` | rocprof | Global memory bytes written | bytes |

## Memory Metrics

| Metric | Source | Description | Unit |
|--------|--------|-------------|------|
| `hbm_bandwidth` | rocm-smi | HBM memory bandwidth | GB/s |
| `vram_bandwidth` | rocm-smi | VRAM bandwidth utilization | GB/s |
| `l2_cache_hit_rate` | rocprof | L2 cache hit rate | % |
| `tlb_hit_rate` | rocprof | TLB hit rate | % |

## CU (Compute Unit) Metrics

| Metric | Source | Description | Unit |
|--------|--------|-------------|------|
| `cu_active` | rocprof | Active CUs | count |
| `cu_occupancy` | rocprof | CU wavefront occupancy | % |
| `cu_stall_math_pipe` | rocprof | CU stalls waiting for math pipe | cycles |
| `cu_stall_mem_pipe` | rocprof | CU stalls waiting for memory pipe | cycles |
| `cu_stall_lds` | rocprof | CU stalls waiting for LDS | cycles |
| `cu_stall_scalar` | rocprof | CU stalls waiting for scalar unit | cycles |

## AMD GPU Architecture Reference

### MI250X (gfx90a)
- CUs: 104 (2 MCD)
- HBM BW: 3200 GB/s
- Peak FP64: 383 TFLOPS
- Peak FP32: 191.5 TFLOPS
- L2 Cache: 8 MB
- Registers per CU: 65536

### MI300X (gfx942)
- CUs: 304
- HBM BW: 5300 GB/s
- Peak FP32: 163.4 TFLOPS
- L2 Cache: 256 MB

### RX 7900 XTX (gfx1100)
- CUs: 96
- HBM BW: 850 GB/s
- Peak FP32: 61.4 TFLOPS
- L2 Cache: 6 MB

### RX 7900 XT (gfx1101)
- CUs: 84
- HBM BW: 512 GB/s
- Peak FP32: 35.2 TFLOPS

## Bottleneck Classification

| Type | Detection Criteria | Typical Solutions |
|------|--------------------|-------------------|
| **Compute** | GPU util > 90%, mem util low | Mixed precision, algorithmic optimization |
| **Memory** | GPU util < 70%, mem util > 80% | Tiling, channels_last, data reuse |
| **Idle** | GPU util < 20% mean | Fix CPU pipeline, async ops |
| **Thermal** | Temperature > 95°C | Better cooling, lower power limit |
| **Power** | Sustained near TDP | Reduce workload, optimize efficiency |
| **Clock Instability** | High clock variance | Check thermal/power limits |

## Collection Interval Guide

| Interval | Overhead | Accuracy | Use Case |
|----------|----------|----------|----------|
| 10 ms | High | Very High | Kernel-level profiling |
| 50 ms | Medium | High | Detailed analysis |
| 100 ms | Low | Good | General profiling |
| 500 ms | Minimal | Moderate | Long monitoring |
| 1000 ms | Negligible | Low | Background monitoring |
