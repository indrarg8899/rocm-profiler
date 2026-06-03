# Multi-stage build for ROCm Profiler
FROM rocm/rocm-terminal:6.0

LABEL maintainer="indrarg8899"
LABEL description="ROCm GPU profiling dashboard"

# Install Python and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /rocm-profiler

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install package
RUN pip3 install -e .

# Create output directory
RUN mkdir -p /output

# Default command: profile help
CMD ["python3", "-m", "src.profiler", "--help"]
