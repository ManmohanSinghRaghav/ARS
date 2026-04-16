"""
Pipeline runner — orchestrates a full ARS research run and persists results to Firestore.
Runs the pipeline in a background thread so the API responds immediately.
"""

import os
import threading
import traceback
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Optional

from app.pipeline.crew import run_crew_pipeline, refine_paper
from app.pipeline.compiler import compile_latex_to_pdf
from app.pipeline.progress import add_step, clear as clear_progress
from app.pipeline.runtime_context import set_tavily_api_key, set_run_id
from app.config import get_settings

def run_pipeline(topic: str, user_id: str, db,
                 llm_config: Optional[dict] = None,
                 tavily_api_key: str = "") -> dict:
    """
    Create a ResearchRun record and launch the pipeline in a background thread.
    Returns the run immediately with status='running'.
    """
    # Create the run record in Firestore
    run_ref = db.collection("runs").document()
    run_id = run_ref.id
    run_data = {
        "id": run_id,
        "user_id": user_id,
        "topic": topic,
        "status": "running",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "hypothesis": "",
        "generated_code": "",
        "execution_output": "",
        "paper_markdown": "",
        "summary_json": {},
        "error_message": "",
    }
    run_ref.set(run_data)

    settings = get_settings()

    # Launch the pipeline in a daemon thread
    thread = threading.Thread(
        target=_execute_pipeline,
        args=(run_id, topic, user_id, llm_config, tavily_api_key,
              settings.OUTPUTS_DIR, settings.LLM_BACKEND, settings.MLX_MODEL,
              settings.OLLAMA_MODEL),
        daemon=True,
    )
    thread.start()

    return run_data


def _execute_pipeline(run_id: str, topic: str, user_id: str,
                      llm_config: Optional[dict], tavily_api_key: str,
                      outputs_dir: str, default_backend: str,
                      default_mlx: str, default_ollama: str):
    """Background thread: runs the full pipeline and updates the DB record."""
    from app.database import db_client
    if db_client is None:
        print("[Pipeline] Firestore client unavailable; aborting background run.")
        return
    run_ref = db_client.collection("runs").document(run_id)

    telemetry_enabled = bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")) or (
        os.getenv("TRACELOOP_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    )

    span_cm = nullcontext()
    if telemetry_enabled:
        try:
            from opentelemetry import trace
            tracer = trace.get_tracer("ars.pipeline")
            span_cm = tracer.start_as_current_span("ars.run")
        except Exception:
            span_cm = nullcontext()

    with span_cm as span:
        if span is not None:
            try:
                span.set_attribute("ars.run_id", run_id)
            except Exception:
                pass

        try:
            set_tavily_api_key(tavily_api_key)
            set_run_id(run_id)
            add_step(run_id, 0, 10, "Initializing CrewAI pipeline", "running")

            # Kickoff Crew
            result = run_crew_pipeline(
                topic=topic,
                run_id=run_id,
                llm_config=llm_config,
            )

            backend = (llm_config or {}).get("llm_backend", default_backend or "ollama")
            model_name = (
                (llm_config or {}).get("mlx_model", default_mlx)
                if backend == "mlx"
                else (llm_config or {}).get("ollama_model", default_ollama)
            )

            # CrewAI returns the full LaTeX document
            paper_latex = result.get("final_paper", "")

            # Compile to PDF
            pdf_success = False
            pdf_filename = f"paper_{run_id}.pdf"
            pdf_local_path = os.path.join(outputs_dir, pdf_filename)
            
            if paper_latex:
                print(f"[Pipeline] Compiling LaTeX for run {run_id}...")
                pdf_success = compile_latex_to_pdf(paper_latex, pdf_local_path)

            # Upload to storage
            from app.database import get_storage_bucket
            storage_bucket = get_storage_bucket()
            if storage_bucket:
                # Upload .tex
                try:
                    tex_blob = storage_bucket.blob(f"runs/{run_id}/paper.tex")
                    tex_blob.upload_from_string(paper_latex, content_type="text/x-tex")
                except Exception as e:
                    print(f"[Pipeline] Warning: Tex upload failed: {e}")
                
                # Upload .pdf
                if pdf_success:
                    try:
                        pdf_blob = storage_bucket.blob(f"runs/{run_id}/paper.pdf")
                        pdf_blob.upload_from_filename(pdf_local_path, content_type="application/pdf")
                    except Exception as e:
                        print(f"[Pipeline] Warning: PDF upload failed: {e}")

            run_ref.update({
                "status": "completed",
                "hypothesis": result.get("hypothesis", ""),
                "generated_code": "", 
                "execution_output": result.get("execution_output", ""),
                "paper_markdown": paper_latex,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })

        except Exception as e:
            run_ref.update({
                "status": "failed",
                "error_message": f"{type(e).__name__}: {e}",
            })
            add_step(run_id, 0, 10, f"Pipeline failed: {e}", "error")
            print(f"[Pipeline] FAILED: {e}")
            traceback.print_exc()

        finally:
            def _cleanup():
                import time
                time.sleep(30)
                clear_progress(run_id)
            threading.Thread(target=_cleanup, daemon=True).start()
def refine_pipeline(run_id: str, feedback: str, user_id: str, db, 
                    llm_config: Optional[dict] = None) -> dict:
    """
    Launch a refinement pipeline in a background thread for an existing run.
    """
    run_ref = db.collection("runs").document(run_id)
    run_ref.update({"status": "refining"})
    
    thread = threading.Thread(
        target=_execute_refinement,
        args=(run_id, feedback, user_id, llm_config),
        daemon=True,
    )
    thread.start()
    
    return {"status": "refining", "run_id": run_id}

def _execute_refinement(run_id: str, feedback: str, user_id: str, llm_config: Optional[dict]):
    """Background thread: runs paper refinement and updates the DB record."""
    from app.database import db_client
    if db_client is None: return
    run_ref = db_client.collection("runs").document(run_id)
    
    try:
        set_run_id(run_id)
        add_step(run_id, 0, 10, f"Refining paper based on feedback: {feedback[:30]}...", "running")
        
        refined_paper = refine_paper(
            original_paper_id=run_id,
            feedback=feedback,
            run_id=run_id,
            db=db_client,
            llm_config=llm_config
        )
        
        # Upload refined paper to storage
        from app.database import get_storage_bucket
        storage_bucket = get_storage_bucket()
        if storage_bucket:
            try:
                blob = storage_bucket.blob(f"runs/{run_id}/paper.md")
                blob.upload_from_string(refined_paper, content_type="text/markdown")
            except Exception as e:
                print(f"[Pipeline] Warning: Failed to upload refined paper: {e}")
                
        run_ref.update({
            "status": "completed",
            "paper_markdown": refined_paper,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        add_step(run_id, 10, 10, "Refinement complete", "done")
        
    except Exception as e:
        run_ref.update({"status": "failed", "error_message": str(e)})
        add_step(run_id, 0, 10, f"Refinement failed: {e}", "error")
        traceback.print_exc()
