"""
Pipeline runner — orchestrates a full ARS research run and persists results to Firestore.
Runs the pipeline in a background thread so the API responds immediately.
"""

import threading
import traceback
from datetime import datetime, timezone
from typing import Optional

from app.pipeline.crew import run_crew_pipeline
from app.pipeline.progress import add_step, clear as clear_progress
from app.pipeline.runtime_context import set_tavily_api_key
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

    try:
        set_tavily_api_key(tavily_api_key)
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

        # CrewAI returns the markdown paper, hypothesis overview, and execution run stats
        run_ref.update({
            "status": "completed",
            "hypothesis": result.get("hypothesis", ""),
            "generated_code": "", # Removed explicitly to just rely on execution output logs
            "execution_output": result.get("execution_output", ""),
            "paper_markdown": result.get("final_paper", ""),
            "summary_json": {
                "topic": topic,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "llm_backend": backend,
                "model": model_name,
                **result.get("summary_data", {})
            },
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
