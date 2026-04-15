"""
Research runs router — start, list, view, download, delete, progress.
Uses Firestore instead of SQLAlchemy.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse, Response
from typing import List

from app.database import get_db
from app.auth.dependencies import User, get_current_user
from app.schemas.run import RunCreate
from app.pipeline.runner import run_pipeline
from app.pipeline.progress import get_steps
from app.config import get_settings
from app.security.crypto import decrypt_str

router = APIRouter(prefix="/api/runs", tags=["Runs"])


def _get_user_llm_config(user: User, db) -> tuple[dict, str]:
    """Build LLM config dict and tavily key from user settings + server defaults."""
    settings = get_settings()
    doc = db.collection("user_settings").document(user.id).get()
    us = doc.to_dict() if doc.exists else {}

    def _dec(field: str) -> str:
        try:
            return decrypt_str(us.get(field))
        except Exception as e:
            # If decryption fails, treat as unset so runs don't crash unexpectedly.
            print(f"[Runs] Warning: failed to decrypt setting '{field}' for user {user.id}: {e}")
            return ""

    llm_config = {
        "llm_backend": (us.get("llm_backend") if us.get("llm_backend") else "") or settings.LLM_BACKEND,
        "gemini_api_key": (_dec("gemini_api_key") if us.get("gemini_api_key") else "") or settings.GEMINI_API_KEY,
        "groq_api_key": (_dec("groq_api_key") if us.get("groq_api_key") else "") or settings.GROQ_API_KEY,
        "mlx_model": (us.get("mlx_model") if us.get("mlx_model") else "") or settings.MLX_MODEL,
        "ollama_model": (us.get("ollama_model") if us.get("ollama_model") else "") or settings.OLLAMA_MODEL,
        "ollama_url": (us.get("ollama_url") if us.get("ollama_url") else "") or settings.OLLAMA_URL,
    }
    tavily_key = (_dec("tavily_api_key") if us.get("tavily_api_key") else "") or settings.TAVILY_API_KEY

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
    
    # Inject user vibe and commands
    if payload.vibe:
        llm_config["vibe"] = payload.vibe
    if payload.commands:
        llm_config["commands"] = payload.commands

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
    """Download the research paper as a Markdown file from Storage (if configured) or Firestore."""
    doc = db.collection("runs").document(run_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    from app.config import get_settings
    from app.database import get_storage_bucket
    
    settings = get_settings()
    paper_markdown = ""
    
    # Try to fetch from storage if bucket is configured
    if settings.FIREBASE_STORAGE_BUCKET:
        storage_bucket = get_storage_bucket()
        if storage_bucket:
            try:
                blob = storage_bucket.blob(f"runs/{run_id}/paper.md")
                paper_markdown = blob.download_as_string(raw_download=False).decode("utf-8")
                print(f"[Runs] Paper retrieved from Storage: runs/{run_id}/paper.md")
            except Exception as e:
                print(f"[Runs] Warning: Failed to fetch paper from storage: {e}. Falling back to Firestore.")
                paper_markdown = run.get("paper_markdown", "")
        else:
            paper_markdown = run.get("paper_markdown", "")
    else:
        # Fallback to Firestore if storage not configured
        paper_markdown = run.get("paper_markdown", "")
    
    if not paper_markdown:
        raise HTTPException(status_code=404, detail="No paper available for this run")

    return PlainTextResponse(
        content=paper_markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="paper_{run_id}.md"'},
    )


@router.get("/{run_id}/paper.pdf")
def download_paper_pdf(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Download the research paper as a PDF file."""
    doc = db.collection("runs").document(run_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    paper_md = run.get("paper_markdown") or ""
    if not paper_md:
        raise HTTPException(status_code=404, detail="No paper available for this run")

    # Generate a simple PDF. We use core fonts (Latin-1); unsupported characters
    # are dropped to ensure generation succeeds without bundling extra fonts.
    from fpdf import FPDF

    topic = (run.get("topic") or "Research Paper").strip()
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.multi_cell(0, 8, text=topic)
    pdf.ln(2)
    pdf.set_font("Courier", size=10)

    safe_text = paper_md.encode("latin-1", "ignore").decode("latin-1")
    pdf.multi_cell(0, 5, text=safe_text)

    out = pdf.output(dest="S")
    if isinstance(out, (bytes, bytearray)):
        pdf_bytes = bytes(out)
    else:
        pdf_bytes = out.encode("latin-1", "ignore")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="paper_{run_id}.pdf"'},
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
