"""
Pipeline runner — orchestrates a full ARS research run and persists results to Firestore.
Runs the pipeline in a background thread so the API responds immediately.
"""

import hashlib
import threading
import traceback
from datetime import datetime, timezone
from typing import Optional

from app.pipeline.graph import build_graph
from app.pipeline.progress import add_step, clear as clear_progress
from app.config import get_settings
from app.database import get_db

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
    run_ref = db_client.collection("runs").document(run_id)

    try:
        add_step(run_id, 0, 10, "Initializing pipeline", "running")

        app = build_graph(
            llm_config=llm_config,
            outputs_dir=outputs_dir,
            tavily_api_key=tavily_api_key,
            run_id=run_id,
        )

        thread_id = hashlib.md5(topic.encode()).hexdigest()[:12]
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "research_topic": topic,
            "retrieved_docs": [],
            "knowledge_context": {},
            "final_reasoning": "",
            "critic_feedback": "",
            "critique_count": 0,
            "generated_code": "",
            "execution_output": "",
            "code_feedback": "",
            "code_critique_count": 0,
            "research_paper": "",
            "paper_feedback": "",
            "paper_critique_count": 0,
        }

        result = app.invoke(initial_state, config=config)

        backend = (llm_config or {}).get("llm_backend", default_backend or "ollama")
        model_name = (
            (llm_config or {}).get("mlx_model", default_mlx)
            if backend == "mlx"
            else (llm_config or {}).get("ollama_model", default_ollama)
        )

        run_ref.update({
            "status": "completed",
            "hypothesis": result.get("final_reasoning", ""),
            "generated_code": result.get("generated_code", ""),
            "execution_output": result.get("execution_output", ""),
            "paper_markdown": result.get("research_paper", ""),
            "summary_json": {
                "topic": topic,
                "hypothesis": result.get("final_reasoning", "")[:500],
                "hypothesis_iterations": result.get("critique_count", 0),
                "code_iterations": result.get("code_critique_count", 0),
                "paper_iterations": result.get("paper_critique_count", 0),
                "paper_word_count": len(result.get("research_paper", "").split()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "llm_backend": backend,
                "model": model_name,
            },
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as e:
        run_ref.update({
            "status": "failed",
            "error_message": f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
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
