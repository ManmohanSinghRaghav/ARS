# ARS (Autonomous Research Scientist) - MLX Version

## ⚠️ Important Compatibility Note

You have selected the **Mac-specific (MLX)** version of this research agent. However, you also requested to run it in **Docker**.

**Please Note:**
- The `mlx` library (Apple Silicon machine learning) **does not run inside Linux**.
- Docker containers run Linux kernels.
- Therefore, **this code cannot run inside a standard Docker container** even on a Mac.

## Recommended Usage (Native macOS)

Instead of Docker, you should run this natively on your Mac (M1/M2/M3) inside a virtual environment.

1.  **Setup**:
    ```bash
    sh run_ars.sh
    ```
    (This script creates a virtual environment, installs `mlx-lm`, and runs the code with full GPU acceleration).

## Docker Warning

The `Dockerfile` included in this repo is for structure/reference only. Attempting to build or run it will result in errors because `pip install mlx-lm` is not supported on Linux systems.
