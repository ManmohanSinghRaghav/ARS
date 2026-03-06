# ARS — Autonomous Research Scientist

A multi-agent pipeline that autonomously searches literature, generates novel hypotheses, writes experiment code, executes it, and produces research papers — powered by a local LLM via **MLX** (macOS) or **Ollama** (any platform).

Now with a **FastAPI** backend (REST API + JWT auth) and a **React** frontend.

## Architecture

### Pipeline

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
| **Save** | Writes paper + summary to database |

### Project Structure

```
ARS/
├── .env.example          # Environment config template
├── .gitignore
├── README.md
├── .venv/                # Python virtual environment (git-ignored)
├── backend/
│   ├── Dockerfile        # Single Docker image (backend only)
│   ├── .env.example      # Backend env template
│   ├── requirements.txt  # Python dependencies
│   └── app/
│       ├── main.py       # FastAPI entry point
│       ├── config.py     # Pydantic settings
│       ├── database.py   # SQLAlchemy setup
│       ├── auth/         # JWT auth, hashing, dependencies
│       ├── models/       # ORM models (User, Run, Settings)
│       ├── schemas/      # Pydantic request/response schemas
│       ├── routers/      # API endpoints (auth, runs, settings)
│       └── pipeline/     # LangGraph research pipeline
│           ├── graph.py  # StateGraph builder
│           ├── nodes.py  # 10 agent node functions
│           ├── runner.py # Pipeline orchestrator
│           ├── llm.py    # LLM dispatcher (MLX/Ollama)
│           ├── helpers.py
│           └── state.py  # AgentState TypedDict
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── App.tsx       # Routes & layout
        ├── api/          # Axios client with JWT
        ├── auth/         # AuthContext & ProtectedRoute
        ├── pages/        # Dashboard, RunDetail, History, Settings
        └── components/   # Navbar, Spinner, RunCard, etc.
```

## Requirements

- **Python** 3.10+
- **Node.js** 18+ (for frontend)
- **One of:**
  - macOS Apple Silicon for MLX backend
  - [Ollama](https://ollama.com) installed & running for Ollama backend (any OS)
- **Tavily API key** ([tavily.com](https://tavily.com)) for web search

## Quick Start

### 1. Backend Setup

```bash
cd ARS

# Create virtual environment (if not exists)
python -m venv .venv

# Activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment
cp .env.example backend/.env
# Edit backend/.env — set TAVILY_API_KEY and SECRET_KEY

# Run backend
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend API available at `http://localhost:8000` — docs at `/docs`.

### 2. Frontend Setup

```bash
cd ARS/frontend
npm install
npm run dev
```

Frontend available at `http://localhost:3000` — proxies `/api` to backend.

### 3. Docker (Backend Only)

```bash
cd ARS/backend

# Build
docker build -t ars-backend .

# Run (Ollama on host)
docker run --rm -p 8000:8000 \
  --env-file .env \
  -v "$(pwd)/outputs:/app/outputs" \
  ars-backend
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | — | Register new user |
| POST | `/api/auth/login` | — | Login, get JWT tokens |
| POST | `/api/auth/refresh` | — | Refresh access token |
| GET | `/api/auth/me` | ✓ | Current user info |
| POST | `/api/runs` | ✓ | Start research pipeline |
| GET | `/api/runs` | ✓ | List user's runs |
| GET | `/api/runs/{id}` | ✓ | Get run details |
| GET | `/api/runs/{id}/paper` | ✓ | Download paper as .md |
| DELETE | `/api/runs/{id}` | ✓ | Delete a run |
| GET | `/api/settings` | ✓ | Get user LLM settings |
| PUT | `/api/settings` | ✓ | Update user LLM settings |
| GET | `/api/health` | — | Health check |

## Configuration

All settings are in `backend/.env` (copy from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./ars.db` | Database connection |
| `SECRET_KEY` | *(change me)* | JWT signing secret |
| `TAVILY_API_KEY` | *(required)* | Web search API key |
| `LLM_BACKEND` | auto-detect | `mlx` (macOS) or `ollama` |
| `MLX_MODEL` | `mlx-community/Qwen2.5-3B-Instruct-bf16` | MLX model ID |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Ollama model tag |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |

## Known Limitations

- **Code execution is unsandboxed** — LLM-generated code runs with full system access via `subprocess`. Use in a VM or container if concerned about safety.
- **3B model quality** — Qwen2.5-3B produces reasonable but not state-of-the-art results. For better output, use a larger model (e.g., `qwen2.5:14b` via Ollama).
- **Blocking pipeline** — Research runs are synchronous (5-30 min). The frontend shows a spinner during execution.
