# ────────────────────────────────────────────────
# ARS — Autonomous Research Scientist  (Ollama backend)
# ────────────────────────────────────────────────
# Uses Ollama REST API for LLM inference inside the container.
# The Ollama server can run on the host or in a companion container.
#
# Build:
#   docker build -t ars .
#
# Run (Ollama on host):
#   docker run --rm -it \
#     --env-file .env \
#     -e LLM_BACKEND=ollama \
#     -e OLLAMA_URL=http://host.docker.internal:11434 \
#     -v "$(pwd)/outputs:/app/outputs" \
#     ars
# ────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python deps — skip macOS-only packages
RUN pip install --no-cache-dir \
    $(grep -v 'sys_platform.*darwin' requirements.txt | grep -v '^#' | grep -v '^$')

COPY main.py .
COPY .env.example .env.example

# Force Ollama backend inside containers (MLX is macOS-only)
ENV LLM_BACKEND=ollama
ENV OLLAMA_URL=http://host.docker.internal:11434

CMD ["python", "main.py"]
