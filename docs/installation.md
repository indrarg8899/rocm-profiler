# Installation

## From pip

```bash
pip install rocm-profiler
```

## From source

```bash
git clone https://github.com/indrarg8899/rocm-profiler.git
cd rocm-profiler
pip install -e .
```

## Dependencies

- Python 3.10+
- `rocm-smi` (part of ROCm)
- Optional: `roctracer` for kernel profiling
- Optional: `fastapi` + `uvicorn` for web dashboard

## Verify

```bash
rocm-profiler monitor --interval 1
```

## GPU Requirements

- AMD GPU with ROCm 6.0+ drivers
- `/sys/class/drm/card*` accessible
- `rocm-smi` in PATH
