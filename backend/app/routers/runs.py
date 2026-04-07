"""
Research runs router — start, list, view, download, delete, progress.
Uses Firestore instead of SQLAlchemy.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from typing import List

from app.database import get_db
from app.auth.dependencies import User, get_current_user
from app.schemas.run import RunCreate
from app.pipeline.runner import run_pipeline
from app.pipeline.progress import get_steps
from app.config import get_settings

router = APIRouter(prefix="/api/runs", tags=["Runs"])


def _get_user_llm_config(user: User, db) -> tuple[dict, str]:
    """Build LLM config dict and tavily key from user settings + server defaults."""
    settings = get_settings()
    doc = db.collection("user_settings").document(user.id).get()
    us = doc.to_dict() if doc.exists else {}

    llm_config = {
        "llm_backend": (us.get("llm_backend") if us.get("llm_backend") else "") or settings.LLM_BACKEND,
        "mlx_model": (us.get("mlx_model") if us.get("mlx_model") else "") or settings.MLX_MODEL,
        "ollama_model": (us.get("ollama_model") if us.get("ollama_model") else "") or settings.OLLAMA_MODEL,
        "ollama_url": (us.get("ollama_url") if us.get("ollama_url") else "") or settings.OLLAMA_URL,
    }
    tavily_key = (us.get("tavily_api_key") if us.get("tavily_api_key") else "") or settings.TAVILY_API_KEY

    return llm_config, tavily_key


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def start_run(
    payload: RunCreate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Start a new research pipeline run."""
    if not payload.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty")

    llm_config, tavily_key = _get_user_llm_config(current_user, db)

    run_data = run_pipeline(
        topic=payload.topic.strip(),
        user_id=current_user.id,
        db=db,
        llm_config=llm_config,
        tavily_api_key=tavily_key,
    )

    return run_data


@router.get("/{run_id}/progress")
def get_run_progress(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Get pipeline progress for a running (or recently completed) run."""
    doc = db.collection("runs").document(run_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "run_id": run_id,
        "status": run.get("status"),
        "steps": get_steps(run_id),
    }


@router.get("")
def list_runs(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """List the current user's past runs."""
    query = db.collection("runs")
    if current_user.role != "admin":
        query = query.where("user_id", "==", current_user.id)
    
    # ── Temp fix: Remove order_by to avoid Firestore index requirement ──
    # query = query.order_by("created_at", direction="DESCENDING").offset(skip).limit(limit)
    docs = query.stream()

    result = []
    for doc in docs:
        r = doc.to_dict()
        word_count = len(r.get("paper_markdown", "").split()) if r.get("paper_markdown") else 0
        result.append({
            "id": r.get("id"),
            "topic": r.get("topic"),
            "status": r.get("status"),
            "paper_word_count": word_count,
            "created_at": r.get("created_at"),
            "completed_at": r.get("completed_at"),
        })

    # In-memory sort and pagination since index is missing
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result[skip : skip + limit]


@router.get("/{run_id}")
def get_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Get full details of a specific run."""
    doc = db.collection("runs").document(run_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return run


@router.get("/{run_id}/paper", response_class=PlainTextResponse)
def download_paper(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Download the research paper as a Markdown file."""
    doc = db.collection("runs").document(run_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    if not run.get("paper_markdown"):
        raise HTTPException(status_code=404, detail="No paper available for this run")

    return PlainTextResponse(
        content=run.get("paper_markdown"),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="paper_{run_id}.md"'},
    )


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Delete a run."""
    doc_ref = db.collection("runs").document(run_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    doc_ref.delete()
