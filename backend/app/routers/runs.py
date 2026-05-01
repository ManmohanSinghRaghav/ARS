"""
Research runs router — start, list, view, download, delete, progress.
Uses Firestore instead of SQLAlchemy.
"""

import json
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
            print(f"[Runs] Warning: failed to decrypt setting '{field}' for user {user.id}: {e}")
            return ""

    llm_config = {
        "gemini_api_key": (_dec("gemini_api_key") if us.get("gemini_api_key") else "") or settings.GEMINI_API_KEY,
        "groq_api_key": (_dec("groq_api_key") if us.get("groq_api_key") else "") or settings.GROQ_API_KEY,
        "openai_api_key": (_dec("openai_api_key") if us.get("openai_api_key") else "") or settings.OPENAI_API_KEY,
        "claude_api_key": (_dec("claude_api_key") if us.get("claude_api_key") else "") or settings.CLAUDE_API_KEY,
        "ollama_model": us.get("ollama_model") or settings.OLLAMA_MODEL,
        "ollama_url": us.get("ollama_url") or settings.OLLAMA_URL,
        # Dynamic model tiers
        "heavy_model": us.get("heavy_model") or settings.DEFAULT_HEAVY_MODEL,
        "heavy_rpm": us.get("heavy_rpm") or settings.DEFAULT_HEAVY_RPM,
        "heavy_tpm": us.get("heavy_tpm") or settings.DEFAULT_HEAVY_TPM,
        "heavy_fallback_model": us.get("heavy_fallback_model") or settings.DEFAULT_HEAVY_FALLBACK_MODEL,
        "heavy_fallback_rpm": us.get("heavy_fallback_rpm") or settings.DEFAULT_HEAVY_FALLBACK_RPM,
        "heavy_fallback_tpm": us.get("heavy_fallback_tpm") or settings.DEFAULT_HEAVY_FALLBACK_TPM,
        "light_model": us.get("light_model") or settings.DEFAULT_LIGHT_MODEL,
        "light_rpm": us.get("light_rpm") or settings.DEFAULT_LIGHT_RPM,
        "light_tpm": us.get("light_tpm") or settings.DEFAULT_LIGHT_TPM,
        "light_fallback_model": us.get("light_fallback_model") or settings.DEFAULT_LIGHT_FALLBACK_MODEL,
        "light_fallback_rpm": us.get("light_fallback_rpm") or settings.DEFAULT_LIGHT_FALLBACK_RPM,
        "light_fallback_tpm": us.get("light_fallback_tpm") or settings.DEFAULT_LIGHT_FALLBACK_TPM,
        "execution_enabled": us.get("execution_enabled", settings.EXECUTION_ENABLED),
        "vibe": us.get("vibe", "Deep Academic"),
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
    
    # NEW: Manual Execution Toggle from UI
    llm_config["execution_enabled"] = payload.execution_enabled

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
        paper_json = r.get("paper_json", {})
        sections = paper_json.get("sections", []) if isinstance(paper_json, dict) else []
        word_count = sum(len(str(s.get("content") or "").split()) for s in sections if isinstance(s, dict))
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
        media_type="text/x-tex",
        headers={"Content-Disposition": f'attachment; filename="paper_{run_id}.tex"'},
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

    # 2. Try Generating from JSON (Pro Engine)
    run = doc.to_dict()
    paper_json = run.get("paper_json")
    if paper_json:
        from app.pipeline.pro_pdf import generate_pro_pdf
        try:
            pdf_bytes = generate_pro_pdf(paper_json)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="paper_{run_id}.pdf"'},
            )
        except Exception as e:
            print(f"[Runs] Error generating Pro PDF: {e}")

    raise HTTPException(status_code=404, detail="Paper content not found for PDF generation.")


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
            # Delete paper.tex and paper.pdf if they exist
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
    """Manually update the paper JSON for a run."""
    doc_ref = db.collection("runs").document(run_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")

    run = doc.to_dict()  # ← was missing, causing NameError
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    current_version = run.get("version", 0)
    client_version = payload.get("version", 0)

    # ── Check Version Conflict ──
    if client_version < current_version:
        raise HTTPException(
            status_code=409,
            detail={"message": "Version conflict detected.", "current_version": current_version, "paper_json": run.get("paper_json")}
        )

    new_version = current_version + 1
    new_json = payload.get("paper_json")
    if not new_json:
        raise HTTPException(status_code=400, detail="paper_json is required")

    # Update Firestore
    doc_ref.update({
        "paper_json": new_json,
        "version": new_version
    })

    # Update Storage if available (graceful — bucket may not exist)
    try:
        from app.config import get_settings
        from app.database import get_storage_bucket
        settings = get_settings()
        if settings.FIREBASE_STORAGE_BUCKET:
            bucket = get_storage_bucket()
            if bucket:
                blob = bucket.blob(f"runs/{run_id}/paper.json")
                blob.upload_from_string(json.dumps(new_json), content_type="application/json")
    except Exception as e:
        print(f"[Runs] Warning: Storage upload failed (non-fatal): {e}")

    return {"status": "success", "message": "Paper JSON updated", "version": new_version}

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

@router.post("/{run_id}/chat")
async def run_grounded_chat(
    run_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Chat with a specific paper using its content as context."""
    doc_ref = db.collection("runs").document(run_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    llm_config, _ = _get_user_llm_config(current_user, db)
    messages = payload.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="messages are required")

    # Use reasoning engine to detect if this is a question or an edit command
    from app.pipeline.llm_factory import get_tier_llm
    llm = get_tier_llm("reasoning", llm_config)  # Fix #4: pass llm_config
    
    last_message = messages[-1]['content']
    intent_prompt = f"""Analyze the user's message: "{last_message}"
    Is the user asking for a CHANGE, EDIT, or UPDATE to the research paper content? 
    Reply with ONLY 'EDIT' or 'QUESTION'.
    """
    intent = llm.call(intent_prompt).strip().upper()

    if 'EDIT' in intent:
        # Trigger refinement in background
        refine_pipeline(
            run_id=run_id,
            feedback=last_message,
            user_id=current_user.id,
            db=db,
            llm_config=llm_config
        )
        return {
            "content": "I've detected an edit request. I am now re-engaging the Swarm to refine the manuscript based on your feedback. Please monitor the Live PDF for updates.",
            "action_triggered": "refining"
        }

    # Otherwise, proceed with normal grounded QA
    paper_json = run.get("paper_json", {})
    paper_content = json.dumps(paper_json, indent=2)
    history = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
    
    system_prompt = f"You are the ARS Research Assistant. Answer questions about the following research paper. Use ONLY the provided context.\n\nPaper Content:\n{paper_content[:20000]}"
    full_prompt = f"{system_prompt}\n\nHistory:\n{history}\n\nASSISTANT:"
    
    try:
        response = llm.call(full_prompt)
        return {"content": response.strip(), "action_triggered": "chat"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grounded chat failed: {e}")


@router.patch("/{run_id}/paper/sections/{section_id}")
def update_section(
    run_id: str,
    section_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """CRUD: Update a specific section in paper_json by section id."""
    doc_ref = db.collection("runs").document(run_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    paper_json = run.get("paper_json", {})
    sections = paper_json.get("sections", [])
    updated = False
    for i, s in enumerate(sections):
        if s.get("id") == section_id:
            sections[i] = {**s, **payload}
            updated = True
            break
    if not updated:
        raise HTTPException(status_code=404, detail="Section not found")

    paper_json["sections"] = sections
    new_version = run.get("version", 0) + 1
    doc_ref.update({"paper_json": paper_json, "version": new_version})
    return {"status": "ok", "version": new_version}


@router.post("/{run_id}/paper/sections")
def add_section(
    run_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """CRUD: Append a new section to paper_json."""
    doc_ref = db.collection("runs").document(run_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    paper_json = run.get("paper_json", {})
    sections = paper_json.get("sections", [])
    sections.append(payload)
    paper_json["sections"] = sections
    new_version = run.get("version", 0) + 1
    doc_ref.update({"paper_json": paper_json, "version": new_version})
    return {"status": "ok", "version": new_version}


@router.delete("/{run_id}/paper/sections/{section_id}", status_code=204)
def delete_section(
    run_id: str,
    section_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """CRUD: Delete a section from paper_json by id."""
    doc_ref = db.collection("runs").document(run_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")
    run = doc.to_dict()
    if run.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    paper_json = run.get("paper_json", {})
    sections = [s for s in paper_json.get("sections", []) if s.get("id") != section_id]
    paper_json["sections"] = sections
    new_version = run.get("version", 0) + 1
    doc_ref.update({"paper_json": paper_json, "version": new_version})
