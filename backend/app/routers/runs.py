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
from app.pipeline.runner import run_pipeline, refine_pipeline
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
        from google.cloud.firestore import FieldFilter
        query = query.where(filter=FieldFilter("user_id", "==", current_user.id))
    
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
                # Priority 1: paper.tex
                blob = storage_bucket.blob(f"runs/{run_id}/paper.tex")
                content = blob.download_as_string(raw_download=False).decode("utf-8")
                return PlainTextResponse(
                    content=content,
                    media_type="text/x-tex",
                    headers={"Content-Disposition": f'attachment; filename="paper_{run_id}.tex"'},
                )
            except Exception:
                # Priority 2: paper.md
                try:
                    blob = storage_bucket.blob(f"runs/{run_id}/paper.md")
                    content = blob.download_as_string(raw_download=False).decode("utf-8")
                    return PlainTextResponse(
                        content=content,
                        media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="paper_{run_id}.md"'},
                    )
                except Exception:
                    pass

    # Fallback to Firestore
    content = run.get("paper_markdown", "")
    if not content:
        raise HTTPException(status_code=404, detail="No paper available for this run")

    return PlainTextResponse(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="paper_{run_id}.txt"'},
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

    import os
    settings = get_settings()
    from app.database import get_storage_bucket
    
    # 1. Try Storage
    if settings.FIREBASE_STORAGE_BUCKET:
        bucket = get_storage_bucket()
        if bucket:
            try:
                blob = bucket.blob(f"runs/{run_id}/paper.pdf")
                if blob.exists():
                    pdf_bytes = blob.download_as_bytes()
                    return Response(
                        content=pdf_bytes,
                        media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="paper_{run_id}.pdf"'},
                    )
            except Exception:
                pass

    # 2. Try Local outputs
    pdf_local = os.path.join(settings.OUTPUTS_DIR, f"paper_{run_id}.pdf")
    if os.path.exists(pdf_local):
        with open(pdf_local, "rb") as f:
            pdf_bytes = f.read()
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="paper_{run_id}.pdf"'},
            )

    raise HTTPException(status_code=404, detail="Compiled PDF not found for this run.")


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Delete a run and all associated data (Firestore, Storage, ChromaDB)."""
    doc_ref = db.collection("runs").document(run_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    # 1. Clear ChromaDB embeddings
    try:
        from app.pipeline.rag import clear_run_spans
        clear_run_spans(run_id)
    except Exception as e:
        print(f"[Runs] Warning: Failed to clear ChromaDB spans for {run_id}: {e}")

    # 2. Clear Firebase Storage files
    try:
        from app.database import get_storage_bucket
        bucket = get_storage_bucket()
        if bucket:
            # Delete paper.md and paper.pdf if they exist
            blobs = bucket.list_blobs(prefix=f"runs/{run_id}/")
            for blob in blobs:
                blob.delete()
                print(f"[Runs] Deleted storage blob: {blob.name}")
    except Exception as e:
        print(f"[Runs] Warning: Failed to clear storage for {run_id}: {e}")

    # 3. Clear Firestore subcollections (progress_steps)
    try:
        # Firestore doesn't delete subcollections automatically. 
        # We must delete documents in a batch.
        steps_ref = doc_ref.collection("progress_steps")
        docs = steps_ref.list_documents()
        batch = db.batch()
        count = 0
        for d in docs:
            batch.delete(d)
            count += 1
        if count > 0:
            batch.commit()
            print(f"[Runs] Deleted {count} progress steps from Firestore")
    except Exception as e:
        print(f"[Runs] Warning: Failed to clear subcollections for {run_id}: {e}")

    # 4. Delete the main run document
    doc_ref.delete()
    print(f"[Runs] Successfully deleted run {run_id}")

@router.patch("/{run_id}/paper")
def update_paper(
    run_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Manually update the paper markdown for a run."""
    doc_ref = db.collection("runs").document(run_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    new_content = payload.get("paper_markdown")
    if not new_content:
        raise HTTPException(status_code=400, detail="paper_markdown is required")

    # Update Firestore
    doc_ref.update({"paper_markdown": new_content})
    
    # Update Storage if available
    from app.config import get_settings
    from app.database import get_storage_bucket
    settings = get_settings()
    if settings.FIREBASE_STORAGE_BUCKET:
        bucket = get_storage_bucket()
        if bucket:
            blob = bucket.blob(f"runs/{run_id}/paper.md")
            blob.upload_from_string(new_content, content_type="text/markdown")

    return {"status": "success", "message": "Paper updated manually"}

@router.post("/{run_id}/refine")
def start_refinement(
    run_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Start an AI refinement process on an existing paper."""
    doc_ref = db.collection("runs").document(run_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    feedback = payload.get("feedback")
    if not feedback:
        raise HTTPException(status_code=400, detail="feedback is required")

    llm_config, _ = _get_user_llm_config(current_user, db)
    
    res = refine_pipeline(
        run_id=run_id,
        feedback=feedback,
        user_id=current_user.id,
        db=db,
        llm_config=llm_config
    )
    return res
