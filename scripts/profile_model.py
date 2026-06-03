#!/usr/bin/env python3
"""
Profile a deep learning model with ROCm Profiler.

Usage:
    python scripts/profile_model.py --model resnet50 --framework pytorch --gpu 0
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.profiler import ROCmProfiler


def profile_model(args):
    """Profile a model training/inference loop."""
    print(f"Profiling model: {args.model}")
    print(f"Framework: {args.framework}")
    print(f"Batch size: {args.batch_size}")
    print(f"Iterations: {args.iterations}")

    profiler = ROCmProfiler(
        config=args.config,
        gpu_id=args.gpu,
    )

    # Build the target script command
    if args.framework == "pytorch":
        script = _build_pytorch_script(args)
    elif args.framework == "tensorflow":
        script = _build_tf_script(args)
    elif args.framework == "rocm":
        script = args.command or f"echo 'No command specified for {args.model}'"
    else:
        raise ValueError(f"Unsupported framework: {args.framework}")

    # Write temp script
    script_path = f"/tmp/rocm_profile_{args.model}.py"
    with open(script_path, "w") as f:
        f.write(script)

    print(f"\nGenerated profiling script: {script_path}")
    print(f"Profiling for {args.duration}s...")

    results = profiler.profile(
        command=f"python {script_path}",
        duration=args.duration,
    )

    # Export
    output_base = f"output/profile_{args.model}_{int(time.time())}"
    os.makedirs("output", exist_ok=True)

    profiler.export(results, format="json", output=f"{output_base}.json")
    profiler.export(results, format="csv", output=f"{output_base}.csv")
    profiler.visualize(results, output=f"{output_base}.html")

    print(f"\nResults saved to {output_base}.*")
    return results


def _build_pytorch_script(args):
    return f"""
import torch
import torch.nn as nn
import time

print("Loading model: {args.model}")

# Simple model for profiling demonstration
class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 64, 3, padding=1)
        self.conv2 = nn.Conv2d(64, 128, 3, padding=1)
        self.conv3 = nn.Conv2d(128, 256, 3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(256, 1000)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.relu(self.conv2(x))
        x = self.relu(self.conv3(x))
        x = self.pool(x).flatten(1)
        return self.fc(x)

model = SimpleModel().cuda()
model.train()

optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
criterion = nn.CrossEntropyLoss()

print("Starting training loop...")
for i in range({args.iterations}):
    x = torch.randn({args.batch_size}, 3, 224, 224).cuda()
    y = torch.randint(0, 1000, ({args.batch_size},)).cuda()

    optimizer.zero_grad()
    output = model(x)
    loss = criterion(output, y)
    loss.backward()
    optimizer.step()

    if (i + 1) % 10 == 0:
        print(f"Iteration {{i+1}}/{{args.iterations}} loss={{loss.item():.4f}}")

print("Training complete.")
"""


def _build_tf_script(args):
    return f"""
import tensorflow as tf
print("TF profiling not yet implemented")
print("Use --framework pytorch or --framework rocm --command <cmd>")
"""


def main():
    parser = argparse.ArgumentParser(description="Profile a model with ROCm Profiler")
    parser.add_argument("--model", type=str, default="simple_cnn", help="Model name")
    parser.add_argument("--framework", type=str, default="pytorch", choices=["pytorch", "tensorflow", "rocm"])
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--iterations", type=int, default=100, help="Number of iterations")
    parser.add_argument("--gpu", type=int, default=0, help="GPU device ID")
    parser.add_argument("--config", type=str, default="configs/tracing.yml")
    parser.add_argument("--duration", type=float, default=30, help="Profiling duration (s)")
    parser.add_argument("--command", type=str, default=None, help="Custom command (for --framework rocm)")

    args = parser.parse_args()
    profile_model(args)


if __name__ == "__main__":
    main()
