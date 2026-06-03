# Dashboard Guide

## Launch

```bash
rocm-profiler serve --port 3000
```

Open `http://localhost:3000` in browser.

## Features

- **Real-time GPU utilization** with animated progress bars
- **Memory usage** (used/total) per GPU
- **Temperature** monitoring with color-coded alerts
- **Power draw** with limit indicator
- **Clock frequencies** (SM and memory)
- **Multi-GPU** support with tabbed views

## API Endpoints

- `GET /` — Dashboard HTML
- `GET /api/metrics` — Latest metrics (JSON)

## Alert Integration

Dashboard integrates with the alert engine. Alerts fire when thresholds are exceeded and appear in the browser console.
