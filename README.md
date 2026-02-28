# ARS (Autonomous Research Scientist) - MLX Version

This application uses `mlx_lm` to run LLM inference locally on Apple Silicon (macOS) using Metal API.

## Requirements

- **OS**: macOS (specifically Apple Silicon M1/M2/M3)
- **Python**: 3.10+
- **Hardware**: Sufficient RAM (16GB+ recommended for 3B models)

## Setup (Recommended: Native)

Running this natively is highly recommended because `mlx` relies on macOS GPU acceleration which is not available in standard Docker containers.

1.  **Clone/Navigate to directory**:
    ```bash
    cd R:\MiniProject\ARS
    ```

2.  **Create Virtual Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows PowerShell: .\venv\Scripts\Activate.ps1
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure API Key**:
    - Edit `.env` file and set your `TAVILY_API_KEY`.

5.  **Run Application**:
    ```bash
    python main.py
    ```

## Docker Warning

The `Dockerfile` is provided for structure, but **standard Docker containers are Linux-based**.

- `mlx` and `mlx_lm` will **fail to install or run** inside a standard Linux container because they require macOS frameworks.
- There is no official "macOS Docker image" for running Python applications in this way.

If you must run in a containerized environment on macOS, consider using a VM or checking if `mlx` has released experimental Linux support (cpu-only), but performance will be severely degraded compared to native Metal execution.
