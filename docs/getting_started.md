# Getting Started with ROCm Profiler

## Prerequisites

- Linux (Ubuntu 20.04+, RHEL 8+, Fedora 36+)
- Python 3.9+
- AMD GPU with ROCm 5.7+ drivers installed
- `rocm-smi` (included with ROCm drivers)

### Verify ROCm Installation

```bash
# Check ROCm is installed
rocm-smi

# Expected output:
# ===================== ROCm System Management Interface ======================
# GPU[0] : (Card0) ...
```

## Installation

### Option 1: From Source

```bash
git clone https://github.com/indrarg8899/rocm-profiler.git
cd rocm-profiler

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Option 2: Docker

```bash
docker build -t rocm-profiler docker/
docker run --rm -it \
  --device=/dev/kfd --device=/dev/dri \
  --group-add video \
  rocm-profiler
```

## First Profiling Session

### 1. Quick Test (no target process)

```bash
# Monitor GPU for 10 seconds
python -m src.profiler --monitor --duration 10
```

### 2. Profile a Running Process

```bash
# Find your process
rocm-smi --showpids

# Profile it
python -m src.profiler --pid <PID> --duration 30 --dashboard output.html
```

### 3. Launch and Profile a Command

```bash
python -m src.profiler --command "python train.py" --duration 60 \
  --config configs/default.yml \
  --output results.json \
  --dashboard dashboard.html
```

## Understanding Output

### Terminal Output

The profiler prints a summary table after each session:

```
╔═══════════════════════════════════════════════╗
║ GPU Utilization                               ║
║   Average: 85.3%  Peak: 97.1%  Min: 12.4%   ║
║ Memory Utilization                            ║
║   Average: 62.1%  Peak: 78.3%                ║
║ Temperature                                   ║
║   Average: 72.4°C Peak: 85.1°C               ║
╚═══════════════════════════════════════════════╝
```

### JSON Output

Full profiling data including:

- `session_id`: Unique session identifier
- `summary`: Aggregated stats
- `analysis`: Bottleneck analysis, trends, anomalies
- `raw_metrics`: All collected metric snapshots

### HTML Dashboard

Interactive visualization with:

- Real-time utilization charts
- Power/temperature timeline
- Memory usage graph
- Bottleneck analysis summary
- Detailed statistics table

## Configuration

Edit `configs/default.yml` to customize:

```yaml
collection:
  interval_ms: 100        # Sampling rate (lower = more accurate, more overhead)
  metrics:                 # Metrics to collect
    - gpu_use_percent
    - mem_use_percent
    - temperature
    - power
  tools:
    rocm_smi: true         # Enable rocm-smi collection
    rocprof: false          # Enable kernel tracing (requires root)

analysis:
  bottleneck_detection: true
  threshold_percentile: 90  # P90 threshold for anomaly detection
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `rocm-smi: command not found` | Install ROCm drivers: https://rocm.docs.amd.com |
| `Permission denied on /dev/kfd` | Add user to `video` group: `sudo usermod -aG video $USER` |
| No GPU detected | Check `rocm-smi` works, verify GPU is supported |
| High profiling overhead | Increase `interval_ms` in config |
