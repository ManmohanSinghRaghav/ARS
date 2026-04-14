"""
ARS — Autonomous Research Scientist
FastAPI application entry point.

Run from anywhere:
    uvicorn app.main:app --app-dir backend/ --host 127.0.0.1 --port 8000
Or from backend/:
    uvicorn app.main:app --host 127.0.0.1 --port 8000
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import runs, settings
from app.routers import auth

settings_obj = get_settings()

app = FastAPI(
    title="ARS — Autonomous Research Scientist",
    description="Multi-agent research pipeline API",
    version="1.0.0",
)

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
app.include_router(auth.router)


# ── Startup ──
@app.on_event("startup")
def on_startup():
    os.makedirs(settings_obj.OUTPUTS_DIR, exist_ok=True)
    print("─" * 55)
    print("  ARS Backend — FastAPI")
    print(f"  Database : Firebase Firestore (NoSQL)")
    print(f"  Outputs  : {settings_obj.OUTPUTS_DIR}")
    print("─" * 55)


# ── Health check ──
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ARS Backend"}



