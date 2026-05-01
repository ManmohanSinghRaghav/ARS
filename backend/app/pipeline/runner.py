"""
Pipeline runner — orchestrates a full ARS research run and persists results to Firestore.
Runs the pipeline in a background thread so the API responds immediately.
"""

import os
import json
import threading
import traceback
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Optional

from app.pipeline.crew import run_crew_pipeline, refine_paper
from app.pipeline.progress import add_step, clear as clear_progress
from app.pipeline.runtime_context import set_tavily_api_key, set_run_id, set_llm_config
from app.config import get_settings

def run_pipeline(topic: str, user_id: str, db,
                 llm_config: Optional[dict] = None,
                 tavily_api_key: str = "") -> dict:
    """
    Create a ResearchRun record and launch the pipeline in a background thread.
    Returns the run immediately with status='running'.
    """
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
        "paper_json": {},
        "summary_json": {},
        "error_message": "",
    }
    run_ref.set(run_data)

    settings = get_settings()

    thread = threading.Thread(
        target=_execute_pipeline,
        args=(run_id, topic, user_id, llm_config, tavily_api_key, settings.OUTPUTS_DIR),
        daemon=True,
    )
    thread.start()

    return run_data


def _execute_pipeline(run_id: str, topic: str, user_id: str,
                      llm_config: Optional[dict], tavily_api_key: str,
                      outputs_dir: str):
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
            set_llm_config(llm_config)
            add_step(run_id, 0, 10, "Initializing CrewAI pipeline", "running")

            result = run_crew_pipeline(
                topic=topic,
                run_id=run_id,
                llm_config=llm_config,
            )

            # Extract structured JSON paper
            paper_json = result.get("paper_json", {})

            # Upload JSON to storage if available
            from app.database import get_storage_bucket
            storage_bucket = get_storage_bucket()
            if storage_bucket and paper_json:
                try:
                    json_blob = storage_bucket.blob(f"runs/{run_id}/paper.json")
                    json_blob.upload_from_string(
                        json.dumps(paper_json, indent=2),
                        content_type="application/json"
                    )
                except Exception as e:
                    print(f"[Pipeline] Warning: JSON upload failed: {e}")

            run_ref.update({
                "status": "completed",
                "hypothesis": result.get("hypothesis", ""),
                "generated_code": "",
                "execution_output": result.get("execution_output", ""),
                "paper_json": paper_json,
                "version": 1,
                "summary_json": result.get("summary_data", {}),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })

            # Fix #7: Save paper_json to local file as persistent backup
            try:
                os.makedirs(outputs_dir, exist_ok=True)
                local_path = os.path.join(outputs_dir, f"{run_id}_paper.json")
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump(paper_json, f, indent=2, ensure_ascii=False)
                print(f"[Pipeline] Paper JSON backed up to {local_path}")
            except Exception as e:
                print(f"[Pipeline] Warning: Local JSON backup failed: {e}")

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
    """Launch a refinement pipeline in a background thread for an existing run."""
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
    if db_client is None:
        return
    run_ref = db_client.collection("runs").document(run_id)

    try:
        set_run_id(run_id)
        set_llm_config(llm_config)
        add_step(run_id, 0, 10, f"Refining paper based on feedback: {feedback[:30]}...", "running")

        refined_paper_str = refine_paper(
            original_paper_id=run_id,
            feedback=feedback,
            run_id=run_id,
            db=db_client,
            llm_config=llm_config
        )

        # Parse refined JSON using robust utility
        from app.pipeline.utils import extract_json_from_text
        refined_json = extract_json_from_text(str(refined_paper_str))
        
        if not refined_json:
            print("[Pipeline] Warning: Could not parse refined JSON; using raw fallback.")
            refined_json = {"sections": [{"id": "raw", "type": "content", "title": "Refined Content", "content": str(refined_paper_str)}]}

        run_ref.update({
            "status": "completed",
            "paper_json": refined_json,
            "version": run_ref.get().to_dict().get("version", 0) + 1,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        add_step(run_id, 10, 10, "Refinement complete", "done")

    except Exception as e:
        run_ref.update({"status": "failed", "error_message": str(e)})
        add_step(run_id, 0, 10, f"Refinement failed: {e}", "error")
        traceback.print_exc()
