"""
Build and compile the LangGraph StateGraph.
"""

import os
import sqlite3
from langgraph.graph import StateGraph, END
from app.pipeline.state import AgentState
from app.pipeline.nodes import _make_nodes
from typing import Optional


def build_graph(llm_config: Optional[dict] = None, outputs_dir: str = "outputs",
                tavily_api_key: str = "", run_id: int | None = None):
    """
    Build and compile a fresh LangGraph pipeline with the given configuration.
    Returns the compiled app ready for .invoke().
    """
    nodes = _make_nodes(llm_config=llm_config, outputs_dir=outputs_dir,
                        tavily_api_key=tavily_api_key, run_id=run_id)

    workflow = StateGraph(AgentState)

    workflow.add_node("search_agent", nodes["search_node"])
    workflow.add_node("reader_agent", nodes["reader_node"])
    workflow.add_node("reasoning_agent", nodes["reasoning_node"])
    workflow.add_node("critic_node", nodes["critic_node"])
    workflow.add_node("coder_agent", nodes["coder_node"])
    workflow.add_node("executor_agent", nodes["execute_code_node"])
    workflow.add_node("code_critic_node", nodes["code_critic_node"])
    workflow.add_node("writer_agent", nodes["writer_node"])
    workflow.add_node("paper_novelty_node", nodes["paper_novelty_node"])
    workflow.add_node("save_paper_node", nodes["save_paper_node"])

    workflow.set_entry_point("search_agent")

    # Linear edges
    workflow.add_edge("search_agent", "reader_agent")
    workflow.add_edge("reader_agent", "reasoning_agent")
    workflow.add_edge("reasoning_agent", "critic_node")

    # Hypothesis feedback loop (max 3)
    workflow.add_conditional_edges(
        "critic_node", nodes["check_critic"],
        {"approved": "coder_agent", "revision": "reasoning_agent"}
    )

    workflow.add_edge("coder_agent", "executor_agent")
    workflow.add_edge("executor_agent", "code_critic_node")

    # Code feedback loop (max 3)
    workflow.add_conditional_edges(
        "code_critic_node", nodes["check_code_critic"],
        {"approved": "writer_agent", "revision": "coder_agent"}
    )

    workflow.add_edge("writer_agent", "paper_novelty_node")

    # Paper feedback loop (max 2)
    workflow.add_conditional_edges(
        "paper_novelty_node", nodes["check_paper_critic"],
        {"approved": "save_paper_node", "revision": "writer_agent"}
    )

    workflow.add_edge("save_paper_node", END)

    # Compile with optional SQLite checkpointer
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        ckpt_path = os.path.join(outputs_dir, "checkpoints.sqlite")
        os.makedirs(outputs_dir, exist_ok=True)
        conn = sqlite3.connect(ckpt_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn=conn)
        app = workflow.compile(checkpointer=checkpointer)
        print(f"[Graph] Compiled with SQLite checkpointer → {ckpt_path}")
    except ImportError:
        print("[WARN] langgraph-checkpoint-sqlite not installed — no crash recovery.")
        app = workflow.compile()
    except Exception as e:
        print(f"[WARN] Checkpointer init failed ({e}) — running without persistence.")
        app = workflow.compile()

    return app
