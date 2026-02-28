#!/usr/bin/env bash
# ────────────────────────────────────────────────
# ARS — Setup & Run  (auto-detects macOS vs Linux/WSL)
# ────────────────────────────────────────────────
set -euo pipefail

echo "─────────────────────────────────────────────────────"
echo "  ARS — Autonomous Research Scientist  (setup script)"
echo "─────────────────────────────────────────────────────"

# ── Create virtual environment if missing ──────
if [ ! -d "venv" ]; then
    echo "[Setup] Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "[Setup] Python: $(python --version) @ $(which python)"

# ── Install dependencies ──────────────────────
echo "[Setup] Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# ── Create .env from template if missing ───────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[Setup] Created .env from .env.example — edit it with your API keys."
fi

# ── Auto-detect backend ───────────────────────
OS="$(uname -s)"
if [ "$OS" = "Darwin" ]; then
    echo "[Setup] macOS detected → defaulting to MLX backend"
    echo "        (Set LLM_BACKEND=ollama in .env to override)"
else
    echo "[Setup] $OS detected → defaulting to Ollama backend"
    echo "        Make sure Ollama is running: ollama serve"
    echo "        Pull the model:              ollama pull qwen2.5:3b"
fi

# ── Run ARS ───────────────────────────────────
echo ""
python main.py
