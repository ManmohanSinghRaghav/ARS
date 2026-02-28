# ARS — Autonomous Research Scientist

A multi-agent pipeline that autonomously searches literature, generates novel hypotheses, writes experiment code, executes it, and produces research papers — powered by a local LLM via **MLX** (macOS) or **Ollama** (any platform).

## Architecture

```
Search → Reader → Reasoning ⇄ Critic → Coder → Executor ⇄ Code Critic → Writer ⇄ Paper Critic → Save
                    (max 3)                        (max 3)                   (max 2)
```

**10 agent nodes** connected by a LangGraph `StateGraph` with 3 self-correcting feedback loops.

| Node | Role |
|------|------|
| **Search** | Fetches top-3 ArXiv papers + top-3 Tavily web results |
| **Reader** | LLM extracts structured JSON (domain, findings, gaps, novelty score) |
| **Reasoning** | Generates a novel, testable hypothesis |
| **Critic** | Peer-reviews hypothesis for novelty; APPROVED / REJECTED |
| **Coder** | Writes a self-contained Python experiment |
| **Executor** | Runs the script via subprocess (120s timeout) |
| **Code Critic** | Reviews execution output; APPROVED / REJECTED |
| **Writer** | Composes a full Markdown research paper |
| **Paper Critic** | Journal-editor review for uniqueness & quality |
| **Save** | Writes `*_paper.md` + `*_summary.json` to `outputs/` |

## Requirements

- **Python** 3.10+
- **One of:**
  - macOS Apple Silicon (M1/M2/M3/M4) for MLX backend
  - [Ollama](https://ollama.com) installed and running for Ollama backend (any OS)
- **Tavily API key** ([tavily.com](https://tavily.com)) for web search

## Quick Start

### Option A: macOS with MLX (GPU-accelerated)

```bash
# Clone & enter project
cd ARS

# One-command setup + run:
bash run_ars.sh
```

### Option B: Any platform with Ollama

```bash
# 1. Install Ollama: https://ollama.com/download
# 2. Start server & pull model:
ollama serve &
ollama pull qwen2.5:3b

# 3. Setup Python environment
python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env — set TAVILY_API_KEY and LLM_BACKEND=ollama

# 5. Run
python main.py
```

### Option C: Docker (Ollama on host)

```bash
# Start Ollama on host first
ollama serve &
ollama pull qwen2.5:3b

# Build & run container
docker build -t ars .
docker run --rm -it \
  --env-file .env \
  -e LLM_BACKEND=ollama \
  -e OLLAMA_URL=http://host.docker.internal:11434 \
  -v "$(pwd)/outputs:/app/outputs" \
  ars
```

## Configuration

All settings live in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `TAVILY_API_KEY` | *(required)* | Web search API key |
| `LLM_BACKEND` | auto-detect | `mlx` (macOS) or `ollama` (any) |
| `MLX_MODEL` | `mlx-community/Qwen2.5-3B-Instruct-bf16` | HuggingFace model ID for MLX |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Ollama model tag |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server address |

## Outputs

All generated files go to `outputs/`:

| File | Content |
|------|---------|
| `<topic>_paper.md` | Full research paper in Markdown |
| `<topic>_summary.json` | Run metadata (iterations, timestamps, word count) |
| `generated_experiment.py` | Last experiment code |
| `checkpoints.sqlite` | LangGraph checkpoint DB (enables crash recovery) |

## Crash Recovery

The pipeline uses a SQLite checkpointer. If the process crashes mid-run, re-running with the **same topic** will resume from the last completed node instead of starting over.

## Project Structure

```
ARS/
├── main.py              # All agent nodes, graph, and entry point
├── requirements.txt     # Pinned dependencies (platform-conditional)
├── .env                 # Your local config (git-ignored)
├── .env.example         # Template for .env
├── .gitignore
├── Dockerfile           # Ollama-based container
├── run_ars.sh           # One-command setup for macOS/Linux
├── README.md            # This file
└── outputs/             # Generated papers, code, checkpoints
```

## Known Limitations

- **Code execution is unsandboxed** — LLM-generated code runs with full system access via `subprocess`. Use in a VM or container if concerned about safety.
- **3B model quality** — Qwen2.5-3B produces reasonable but not state-of-the-art results. For better output, use a larger model (e.g., `qwen2.5:14b` via Ollama).
- **Paper length** — Max 4096 tokens for paper generation; very long papers may be truncated.
