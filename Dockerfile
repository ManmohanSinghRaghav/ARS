# Dockerfile for ARS (Autonomous Research Scientist)
#
# CRITICAL WARNING:
# This Dockerfile is based on Linux (standard for Docker).
# Apple's MLX library is currently NOT supported on Linux.
# As such, running `python main.py` inside this container WILL FAIL
# because `mlx-lm` cannot be installed or executed on Linux.
#
# This file is provided for project structure compliance only.
# To run this application, you MUST run it NATIVELY on macOS.

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies
# NOTE: This step will likely FAIL for 'mlx-lm' on Linux architecture
# checks are often needed here. We attempt the install but expect failure.
RUN pip install --no-cache-dir -r requirements.txt || echo "WARNING: MLX installation failed as expected on Linux."

# Copy application code
COPY main.py .

# Entry point
# This will likely crash with an ImportError or PlatformError for MLX
CMD ["python", "main.py"]
