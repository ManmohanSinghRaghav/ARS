"""
Research runs router — start, list, view, download, delete, progress.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.run import ResearchRun
from app.models.settings import UserSettings
from app.schemas.run import RunCreate, RunResponse, RunListItem
from app.auth.dependencies import get_current_user
from app.pipeline.runner import run_pipeline
from app.pipeline.progress import get_steps
from app.config import get_settings

router = APIRouter(prefix="/api/runs", tags=["Runs"])


def _get_user_llm_config(user: User, db: Session) -> tuple[dict, str]:
    """Build LLM config dict and tavily key from user settings + server defaults."""
    settings = get_settings()
    us = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()

    llm_config = {
        "llm_backend": (us.llm_backend if us and us.llm_backend else "") or settings.LLM_BACKEND,
        "mlx_model": (us.mlx_model if us and us.mlx_model else "") or settings.MLX_MODEL,
        "ollama_model": (us.ollama_model if us and us.ollama_model else "") or settings.OLLAMA_MODEL,
        "ollama_url": (us.ollama_url if us and us.ollama_url else "") or settings.OLLAMA_URL,
    }
    tavily_key = (us.tavily_api_key if us and us.tavily_api_key else "") or settings.TAVILY_API_KEY

    return llm_config, tavily_key


@router.post("", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
def start_run(
    payload: RunCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start a new research pipeline run.
    Returns immediately with status='running'. Poll /progress for updates.
    """
    if not payload.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty")

    llm_config, tavily_key = _get_user_llm_config(current_user, db)

    run = run_pipeline(
        topic=payload.topic.strip(),
        user_id=current_user.id,
        db=db,
        llm_config=llm_config,
        tavily_api_key=tavily_key,
    )

    return run


@router.get("/{run_id}/progress")
def get_run_progress(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get pipeline progress for a running (or recently completed) run.
    Returns the current DB status and in-memory progress steps.
    """
    run = db.query(ResearchRun).filter(ResearchRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "run_id": run_id,
        "status": run.status,
        "steps": get_steps(run_id),
    }


@router.get("", response_model=List[RunListItem])
def list_runs(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's past runs (paginated, newest first)."""
    query = db.query(ResearchRun).filter(ResearchRun.user_id == current_user.id)

    # Admin can see all runs
    if current_user.role == "admin":
        query = db.query(ResearchRun)

    runs = query.order_by(ResearchRun.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for r in runs:
        word_count = len(r.paper_markdown.split()) if r.paper_markdown else 0
        result.append(RunListItem(
            id=r.id,
            topic=r.topic,
            status=r.status,
            paper_word_count=word_count,
            created_at=r.created_at,
            completed_at=r.completed_at,
        ))
    return result


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full details of a specific run."""
    run = db.query(ResearchRun).filter(ResearchRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return run


@router.get("/{run_id}/paper", response_class=PlainTextResponse)
def download_paper(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the research paper as a Markdown file."""
    run = db.query(ResearchRun).filter(ResearchRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    if not run.paper_markdown:
        raise HTTPException(status_code=404, detail="No paper available for this run")

    return PlainTextResponse(
        content=run.paper_markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="paper_{run_id}.md"'},
    )


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a run."""
    run = db.query(ResearchRun).filter(ResearchRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    db.delete(run)
    db.commit()
