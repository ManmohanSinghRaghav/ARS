"""
Pipeline runner — orchestrates a full ARS research run and persists results to DB.
Runs the pipeline in a background thread so the API responds immediately.
"""

import hashlib
import threading
import traceback
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.pipeline.graph import build_graph
from app.pipeline.progress import add_step, clear as clear_progress
from app.models.run import ResearchRun
from app.config import get_settings
from app.database import SessionLocal


def run_pipeline(topic: str, user_id: int, db: Session,
                 llm_config: Optional[dict] = None,
                 tavily_api_key: str = "") -> ResearchRun:
    """
    Create a ResearchRun record and launch the pipeline in a background thread.
    Returns the run immediately with status='running'.
    """
    # Create the run record
    run = ResearchRun(
        user_id=user_id,
        topic=topic,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    settings = get_settings()

    # Launch the pipeline in a daemon thread
    thread = threading.Thread(
        target=_execute_pipeline,
        args=(run.id, topic, user_id, llm_config, tavily_api_key,
              settings.OUTPUTS_DIR, settings.LLM_BACKEND, settings.MLX_MODEL,
              settings.OLLAMA_MODEL),
        daemon=True,
    )
    thread.start()

    return run


def _execute_pipeline(run_id: int, topic: str, user_id: int,
                      llm_config: Optional[dict], tavily_api_key: str,
                      outputs_dir: str, default_backend: str,
                      default_mlx: str, default_ollama: str):
    """Background thread: runs the full pipeline and updates the DB record."""
    db = SessionLocal()
    try:
        run = db.query(ResearchRun).filter(ResearchRun.id == run_id).first()
        if not run:
            return

        add_step(run_id, 0, 10, "Initializing pipeline", "running")

        # Build the graph with user config + run_id for progress tracking
        app = build_graph(
            llm_config=llm_config,
            outputs_dir=outputs_dir,
            tavily_api_key=tavily_api_key,
            run_id=run_id,
        )

        # Deterministic thread_id for checkpointing resume
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

        # Extract results
        backend = (llm_config or {}).get("llm_backend", default_backend or "ollama")
        model_name = (
            (llm_config or {}).get("mlx_model", default_mlx)
            if backend == "mlx"
            else (llm_config or {}).get("ollama_model", default_ollama)
        )

        run.status = "completed"
        run.hypothesis = result.get("final_reasoning", "")
        run.generated_code = result.get("generated_code", "")
        run.execution_output = result.get("execution_output", "")
        run.paper_markdown = result.get("research_paper", "")
        run.summary_json = {
            "topic": topic,
            "hypothesis": result.get("final_reasoning", "")[:500],
            "hypothesis_iterations": result.get("critique_count", 0),
            "code_iterations": result.get("code_critique_count", 0),
            "paper_iterations": result.get("paper_critique_count", 0),
            "paper_word_count": len(result.get("research_paper", "").split()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "llm_backend": backend,
            "model": model_name,
        }
        run.completed_at = datetime.now(timezone.utc)

    except Exception as e:
        run.status = "failed"
        run.error_message = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        add_step(run_id, 0, 10, f"Pipeline failed: {e}", "error")
        print(f"[Pipeline] FAILED: {e}")
        traceback.print_exc()

    finally:
        try:
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
            # Schedule progress cleanup after a delay so frontend can poll final state
            def _cleanup():
                import time
                time.sleep(30)
                clear_progress(run_id)
            threading.Thread(target=_cleanup, daemon=True).start()
