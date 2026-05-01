"""
ARS — Autonomous Research Scientist
FastAPI application entry point.

Run from anywhere:
    uvicorn app.main:app --app-dir backend/ --host 127.0.0.1 --port 8000
Or from backend/:
    uvicorn app.main:app --host 127.0.0.1 --port 8000
"""

import os
from pathlib import Path

# ── Opt-in tracing bootstrap (OpenLLMetry via Traceloop) ──
# Kept intentionally conservative:
# - Disabled by default
# - No changes to business logic
# - Avoids loading all .env keys into os.environ (only OTEL_/TRACELOOP_)

def _load_otel_env_from_dotenv(dotenv_path: Path) -> None:
    try:
        if not dotenv_path.exists():
            return
        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            if not (key.startswith("OTEL_") or key.startswith("TRACELOOP_")):
                continue
            val = val.strip().strip("\"").strip("'")
            # Don't override process-level environment.
            os.environ.setdefault(key, val)
    except Exception:
        # Never block app startup on telemetry env parsing.
        return


_project_root = Path(__file__).resolve().parents[2]
_load_otel_env_from_dotenv(_project_root / ".env")

_telemetry_enabled = bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")) or (
    os.getenv("TRACELOOP_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
)

if _telemetry_enabled:
    try:
        from traceloop.sdk import Traceloop

        service_name = (os.getenv("OTEL_SERVICE_NAME") or "ARS-Engine-v3.2.2").strip()
        disable_batching = os.getenv("TRACELOOP_DISABLE_BATCHING", "").strip().lower() in {"1", "true", "yes", "on"}

        # Traceloop reads OTEL_* env vars for exporter config; we avoid hard-coding endpoints in code.
        try:
            Traceloop.init(app_name=service_name, disable_batch=disable_batching)
        except TypeError:
            # Older/newer SDKs may not support disable_batch kwarg.
            Traceloop.init(app_name=service_name)

        # Redis spans (LiteLLM cache + tool cache)
        try:
            from opentelemetry.instrumentation.redis import RedisInstrumentor
            RedisInstrumentor().instrument()
        except Exception as e:
            print(f"[Telemetry] Redis instrumentation unavailable: {e}")

        # Outbound HTTP spans (covers Gemini/Groq, Chroma Cloud, and web search)
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()
        except Exception as e:
            print(f"[Telemetry] HTTPX instrumentation unavailable: {e}")

        try:
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
            RequestsInstrumentor().instrument()
        except Exception as e:
            print(f"[Telemetry] Requests instrumentation unavailable: {e}")

        # Optional Gemini SDK instrumentation (only if installed and in use)
        try:
            from opentelemetry.instrumentation.google_generativeai import GoogleGenerativeAiInstrumentor
            GoogleGenerativeAiInstrumentor().instrument()
        except Exception:
            pass

        print(f"[Telemetry] Enabled (service={service_name})")
    except Exception as e:
        print(f"[Telemetry] Disabled (init failed): {e}")


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import runs, settings, discovery
from app.routers import auth

settings_obj = get_settings()

app = FastAPI(
    title="ARS — Autonomous Research Scientist",
    description="Multi-agent research pipeline API",
    version="1.0.0",
)

# Inbound request tracing (opt-in)
if _telemetry_enabled:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
    except Exception as e:
        print(f"[Telemetry] FastAPI instrumentation unavailable: {e}")

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_obj.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──
app.include_router(runs.router)
app.include_router(settings.router)
app.include_router(discovery.router)
app.include_router(auth.router)


# ── Startup ──
@app.on_event("startup")
def on_startup():
    os.makedirs(settings_obj.OUTPUTS_DIR, exist_ok=True)
    print("=" * 55)
    print("  ARS Backend — FastAPI")
    print(f"  Database : Firebase Firestore (NoSQL)")
    print(f"  Outputs  : {settings_obj.OUTPUTS_DIR}")
    print("=" * 55)


# ── Health check ──
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ARS Backend"}



