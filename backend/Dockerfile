# ────────────────────────────────────────────────
# ARS Backend — FastAPI + LangGraph pipeline
# ────────────────────────────────────────────────
# Build:
#   docker build -t ars-backend .
#
# Run:
#   docker run --rm -p 8000:8000 \
#     --env-file .env \
#     -v "$(pwd)/outputs:/app/outputs" \
#     ars-backend
# ────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System deps (gcc for bcrypt / C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps (skip macOS-only packages automatically via markers)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create outputs directory
RUN mkdir -p /app/outputs

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LLM_BACKEND=ollama
ENV OLLAMA_URL=http://host.docker.internal:11434

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "2700"]
