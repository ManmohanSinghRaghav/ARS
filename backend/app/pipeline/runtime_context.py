"""Per-run runtime context for pipeline execution.

This avoids leaking per-user API keys across concurrent runs by storing
secrets in `contextvars` scoped to the background runner thread.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional


_tavily_api_key: ContextVar[str] = ContextVar("ars_tavily_api_key", default="")
_run_id: ContextVar[str] = ContextVar("ars_run_id", default="")


def set_tavily_api_key(value: Optional[str]) -> None:
    _tavily_api_key.set((value or "").strip())


def get_tavily_api_key() -> str:
    return _tavily_api_key.get()


def set_run_id(value: Optional[str]) -> None:
    _run_id.set((value or "").strip())


def get_run_id() -> str:
    return _run_id.get()
