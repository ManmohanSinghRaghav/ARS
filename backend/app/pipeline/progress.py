"""
In-memory progress tracker for pipeline runs.
Thread-safe dict keyed by run_id, storing a list of step events.
Progress is ephemeral — cleared after the run completes.
"""

import threading
from datetime import datetime, timezone

_progress: dict[int, list[dict]] = {}
_lock = threading.Lock()


def add_step(run_id: int, step: int, total: int, title: str,
             status: str = "running", detail: str = ""):
    """Append a progress event for a run."""
    entry = {
        "step": step,
        "total": total,
        "title": title,
        "status": status,       # running | success | warning | error
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        if run_id not in _progress:
            _progress[run_id] = []
        _progress[run_id].append(entry)


def get_steps(run_id: int) -> list[dict]:
    """Return all progress steps for a run (copy)."""
    with _lock:
        return list(_progress.get(run_id, []))


def clear(run_id: int):
    """Remove progress data for a completed/failed run."""
    with _lock:
        _progress.pop(run_id, None)
