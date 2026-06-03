"""CLI entry point for rocm-profiler."""

import argparse
import sys
import time
from rocm_profiler.metrics import MetricsCollector
from rocm_profiler.exporter import MetricsExporter
from rocm_profiler.dashboard import DashboardServer
from rocm_profiler.alerts import AlertEngine, AlertRule, AlertSeverity, setup_default_rules


def cmd_monitor(args):
    """Monitor GPUs in real-time with optional CSV export."""
    collector = MetricsCollector()
    exporter = MetricsExporter(output_dir=args.output_dir) if args.export else None

    print(f"Monitoring GPUs every {args.interval}s" + (f" → {args.export}" if args.export else ""))

    try:
        while True:
            all_metrics = collector.collect_all()
            for m in all_metrics:
                d = m.to_dict()
                print(
                    f"GPU{d['gpu_id']}: "
                    f"Util={d['utilization_gpu']}% "
                    f"Mem={d['memory_used_mb']:.0f}/{d['memory_total_mb']:.0f}MB "
                    f"Temp={d['temperature_c']}°C "
                    f"Power={d['power_w']}W"
                )

                if exporter:
                    exporter.push_metrics([d]) if hasattr(exporter, 'push_metrics') else None

            if exporter and args.export:
                exporter.export_csv([m.to_dict() for m in all_metrics])

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


def cmd_profile(args):
    """Profile a command's GPU usage."""
    collector = MetricsCollector()
    exporter = MetricsExporter(output_dir=args.output_dir)

    import subprocess
    print(f"Profiling: {' '.join(args.command)}")

    metrics = []
    proc = subprocess.Popen(args.command)

    while proc.poll() is None:
        all_metrics = collector.collect_all()
        for m in all_metrics:
            metrics.append(m.to_dict())
        time.sleep(0.1)

    exit_code = proc.wait()
    print(f"Process exited with code {exit_code}")

    if metrics:
        path = exporter.export_csv(metrics, "profile_metrics")
        json_path = exporter.export_json(metrics, "profile_metrics")
        print(f"Results: {path}, {json_path}")

    return exit_code


def cmd_serve(args):
    """Start the web dashboard."""
    collector = MetricsCollector()
    server = DashboardServer(host=args.host, port=args.port)
    alert_engine = AlertEngine()

    if not args.no_alerts:
        for rule in setup_default_rules():
            alert_engine.add_rule(rule)

    print(f"Starting dashboard at http://{args.host}:{args.port}")
    try:
        while True:
            all_metrics = collector.collect_all()
            for m in all_metrics:
                d = m.to_dict()
                server.push_metrics(d)
                alerts = alert_engine.evaluate(d)
                for a in alerts:
                    print(f"  ⚠️  {a.message}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ROCm Profiler")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    mon = subparsers.add_parser("monitor", help="Monitor GPUs")
    mon.add_argument("--interval", type=float, default=1.0)
    mon.add_argument("--export", action="store_true")
    mon.add_argument("--output-dir", default="./profiler_output")
    mon.set_defaults(func=cmd_monitor)

    prof = subparsers.add_parser("profile", help="Profile a command")
    prof.add_argument("command", nargs="+")
    prof.add_argument("--output-dir", default="./profiler_output")
    prof.set_defaults(func=cmd_profile)

    srv = subparsers.add_parser("serve", help="Start dashboard")
    srv.add_argument("--host", default="0.0.0.0")
    srv.add_argument("--port", type=int, default=3000)
    srv.add_argument("--no-alerts", action="store_true")
    srv.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
