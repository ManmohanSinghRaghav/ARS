"""
In-memory progress tracker for pipeline runs.
Thread-safe dict keyed by run_id, storing a list of step events.
Progress is ephemeral — cleared after the run completes.
"""

import threading
from datetime import datetime, timezone

from app.database import db_client

_progress: dict[str, list[dict]] = {}
_lock = threading.Lock()


def add_step(run_id: str, step: int, total: int, title: str,
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

    # Best-effort persistence for resilience across restarts.
    try:
        if db_client is not None:
            # Auto-id doc so we don't need a counter.
            db_client.collection("runs").document(run_id).collection("progress_steps").document().set(entry)
    except Exception as e:
        # Never break a run due to progress persistence failure.
        print(f"[Progress] Warning: failed to persist progress for run {run_id}: {e}")


def get_steps(run_id: str) -> list[dict]:
    """Return all progress steps for a run (copy)."""
    with _lock:
        steps = list(_progress.get(run_id, []))

    if steps:
        return steps

    # Fallback to Firestore if in-memory cache was cleared or server restarted.
    try:
        if db_client is None:
            return []
        docs = (
            db_client.collection("runs")
            .document(run_id)
            .collection("progress_steps")
            .order_by("timestamp")
            .stream()
        )
        return [d.to_dict() for d in docs]
    except Exception as e:
        print(f"[Progress] Warning: failed to load persisted progress for run {run_id}: {e}")
        return []


def clear(run_id: str):
    """Remove progress data for a completed/failed run."""
    with _lock:
        _progress.pop(run_id, None)
