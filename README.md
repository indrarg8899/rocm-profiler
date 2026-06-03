<p align="center">
  <img src="https://img.shields.io/badge/ROCm-6.0+-red?logo=amd" alt="ROCm">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen" alt="Status">
  <img src="https://img.shields.io/badge/Platform-Linux-blueviolet" alt="Platform">
  <img src="https://img.shields.io/badge/GPU-AMD%20Radeon-blue" alt="GPU">
  <img src="https://img.shields.io/badge/CI-Passing-success" alt="CI">
</p>

<h1 align="center">⚡ ROCm Profiler</h1>

<p align="center">
  <b>Real-time GPU profiling, analysis, and visualization dashboard for AMD ROCm</b>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-sample-output">Sample Output</a> •
  <a href="#-documentation">Docs</a> •
  <a href="#-configuration">Config</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

## 🚀 Features

| Category | Feature | Description |
|----------|---------|-------------|
| **Profiling** | Full GPU Profiling | Capture 200+ hardware counters via `rocm-smi` + `rocprof` |
| **Profiling** | Kernel Analysis | Per-kernel CU occupancy, wavefront utilization, memory throughput |
| **Profiling** | Real-time Monitoring | Live GPU stats streaming with configurable polling intervals |
| **Analysis** | Bottleneck Detection | Automated identification of compute vs memory vs latency bottlenecks |
| **Analysis** | Roofline Modeling | Arithmetic intensity analysis against hardware roofline |
| **Analysis** | Memory Analysis | HBM bandwidth, cache hit rates, TLB efficiency |
| **Analysis** | Occupancy Analysis | Wavefront occupancy vs theoretical maximum |
| **Export** | CSV/JSON Export | Machine-readable profiling data for CI/CD integration |
| **Export** | HTML Dashboard | Interactive charts, heatmaps, flame graphs |
| **Export** | Markdown Reports | Auto-generated profiling summaries |
| **Config** | YAML Profiles | Pre-built configs for deep learning, HPC, compute-bound, memory-bound |
| **Docker** | Containerized | Fully containerized profiling environment |
| **Compare** | Run Comparison | Side-by-side comparison of profiling sessions |

## 📦 Installation

```bash
# From source
git clone https://github.com/indrarg8899/rocm-profiler.git
cd rocm-profiler
pip install -e .

# Via pip (when published)
pip install rocm-profiler

# Docker
docker build -t rocm-profiler docker/
docker run --device=/dev/kfd --device=/dev/dri --cap-add=SYS_PTRACE rocm-profiler
```

## ⚡ Quick Start

```python
from src.profiler import ROCmProfiler

# Start a profiling session
profiler = ROCmProfiler(config="configs/default.yml")

# Profile a target process
results = profiler.profile(pid=12345, duration=30)

# Generate dashboard
profiler.visualize(results, output="dashboard.html")

# Export data
profiler.export(results, format="csv", output="results.csv")
profiler.export(results, format="json", output="results.json")
```

### Command Line

```bash
# Profile a process
python -m src.profiler --pid 12345 --config configs/default.yml --duration 30

# Generate HTML dashboard
python -m src.visualizer --input results.json --output dashboard.html

# Compare two profiling runs
python scripts/compare_runs.py --run1 baseline.json --run2 optimized.json

# Profile a model
python scripts/profile_model.py --model resnet50 --framework pytorch --gpu 0
```

## 📊 Sample Output

```
╔══════════════════════════════════════════════════════════════╗
║               ROCm Profiler Session Report                   ║
╠══════════════════════════════════════════════════════════════╣
║ Target:  PID 12345 (python3)                                ║
║ GPU:     AMD Radeon RX 7900 XTX (gfx1100)                   ║
║ Duration: 30.00s                                             ║
╠══════════════════════════════════════════════════════════════╣
║ GPU UTILIZATION                                              ║
║   Average: 94.7%  │  Peak: 99.2%  │  Min: 12.3%            ║
║   Memory:  14.2 GB / 24.0 GB (59.2%)                        ║
╠══════════════════════════════════════════════════════════════╣
║ TOP KERNELS (by time)                                        ║
║ ┌──────────────────────┬──────────┬─────────┬──────────────┐║
║ │ Kernel               │ Time(ms) │ CU(%)   │ Wavefronts   │║
║ ├──────────────────────┼──────────┼─────────┼──────────────┤║
║ │ conv2d_forward_64    │ 12.45    │ 87.3    │ 2048         │║
║ │ batch_norm_128       │  8.21    │ 92.1    │ 1024         │║
║ │ relu_inplace_256     │  4.87    │ 45.6    │ 512          │║
║ │ matmul_nn_512        │  3.12    │ 96.8    │ 4096         │║
║ │ softmax_1024         │  1.93    │ 78.4    │ 256          │║
║ └──────────────────────┴──────────┴─────────┴──────────────┘║
╠══════════════════════════════════════════════════════════════╣
║ BOTTLENECK ANALYSIS                                          ║
║   ⚠ Memory-bound detected (89.3% of kernels)                ║
║   → HBM bandwidth utilization: 72.4% (614.4/850.0 GB/s)    ║
║   → L2 cache hit rate: 34.2% (LOW - consider tiling)        ║
║   →建议: Increase batch size, use channels_last memory fmt  ║
╠══════════════════════════════════════════════════════════════╣
║ OCCUPANCY                                                     ║
║   Achieved: 78.4% │ Theoretical Max: 100.0%                 ║
║   Limiting Factor: VGPR usage (conv2d_forward_64: 64 VGPRs) ║
╚══════════════════════════════════════════════════════════════╝
```

### HTML Dashboard Preview

The HTML dashboard provides:
- 🔥 Real-time GPU utilization heatmap
- 📈 Kernel execution timeline (flame graph)
- 📊 Memory bandwidth usage over time
- 🎯 Occupancy vs performance scatter plots
- 📋 Detailed per-kernel metrics table
- 🔄 Run comparison overlays

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting_started.md) | Installation, setup, first profiling session |
| [Profiling Guide](docs/profiling_guide.md) | Advanced profiling techniques and workflows |
| [Metrics Reference](docs/metrics_reference.md) | Complete list of collected hardware counters |

## 🔧 Configuration

```yaml
# configs/default.yml
collection:
  interval_ms: 100
  metrics:
    - gpu_use_percent
    - mem_use_percent
    - mem_used
    - temperature
    - power
    - fan_speed
    - clock_speed
    - occupancy
    - wavefronts
    - vram_bytes
  tools:
    rocm_smi: true
    rocprof: false

analysis:
  bottleneck_detection: true
  roofline_analysis: true
  occupancy_analysis: true
  memory_analysis: true
  threshold_percentile: 90

visualization:
  format: html
  theme: dark
  charts:
    - utilization_timeline
    - kernel_flamegraph
    - memory_bandwidth
    - occupancy_scatter
    - bottleneck_summary
  refresh_interval_s: 5

export:
  formats: [csv, json]
  include_metadata: true
  include_kernel_details: true
```

### Pre-built Profiles

| Config | Use Case |
|--------|----------|
| `default.yml` | General-purpose balanced profiling |
| `tracing.yml` | High-frequency kernel tracing with rocprof |

## 🐳 Docker

```bash
# Build
docker build -t rocm-profiler docker/

# Run with GPU access
docker run --rm -it \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add video \
  --cap-add=SYS_PTRACE \
  -v /tmp/rocm-profiler/output:/output \
  rocm-profiler

# Profile a specific command
docker run --rm -it \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  rocm-profiler python scripts/profile_model.py --model resnet50
```

## 🤝 Contributing

```bash
# Fork & clone
git clone https://github.com/YOUR_FORK/rocm-profiler.git
cd rocm-profiler

# Setup dev environment
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linter
flake8 src/ --max-line-length=120
```

## 📋 Requirements

- **OS**: Ubuntu 20.04+ / RHEL 8+
- **GPU**: AMD Radeon with ROCm 5.7+ support
- **Python**: 3.9+
- **ROCm Stack**: `rocm-smi`, `rocprof` (optional)

## 📜 License

MIT License — see [LICENSE](LICENSE)

## ⭐ Star History

If this project helps you profile your GPU workloads, consider giving it a star!

---

<p align="center">
  Built with ❤️ for the ROCm community
</p>
