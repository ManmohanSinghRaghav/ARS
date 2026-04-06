"""
All 10 LangGraph node functions + 3 conditional edge checkers.
Extracted from original main.py and parameterized with LLM config.
"""

import os
import sys
import json
import hopx
from typing import List, Optional

from langchain_community.utilities import ArxivAPIWrapper
from langchain_community.tools.arxiv.tool import ArxivQueryRun

from app.pipeline.state import AgentState
from app.pipeline.llm import safe_llm
from app.pipeline.helpers import (
    section, extract_json, is_approved, strip_code_fences, sanitize_filename
)
from app.pipeline.progress import add_step


def _make_nodes(llm_config: Optional[dict] = None, outputs_dir: str = "outputs",
                tavily_api_key: str = "", run_id: str | None = None):
    """
    Factory that returns all node functions bound to the given config.
    This avoids relying on global state and lets each run use per-user settings.
    """
    cfg = llm_config
    _run_id = run_id  # capture for closures

    # If tavily key provided, set it for this pipeline run
    if tavily_api_key:
        os.environ["TAVILY_API_KEY"] = tavily_api_key

    def _progress(step: int, title: str, status: str = "running", detail: str = ""):
        """Report progress if run_id is set."""
        if _run_id is not None:
            add_step(_run_id, step, 10, title, status, detail)

    # ── 1. Search ─────────────────────────────
    def search_node(state: AgentState) -> dict:
        topic = state["research_topic"]
        section(1, f"Search  —  {topic}", _run_id)
        _progress(1, "Searching literature")
        docs: List[str] = []

        try:
            arxiv = ArxivQueryRun(api_wrapper=ArxivAPIWrapper(top_k_results=3))
            result = arxiv.run(topic)
            docs.append(f"[ArXiv]\n{result}")
            print("  ✓ ArXiv fetched (top 3)")
        except Exception as e:
            print(f"  ✗ ArXiv: {e}")

        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
            tavily = TavilySearchResults(max_results=3)
            results = tavily.invoke({"query": topic})
            if isinstance(results, list):
                for r in results:
                    docs.append(f"[Web: {r.get('url')}]\n{r.get('content', '')}")
                print(f"  ✓ Tavily: {len(results)} results")
            else:
                print(f"  ✗ Tavily unexpected type: {type(results)}")
        except Exception as e:
            print(f"  ✗ Tavily: {e}")

        if not docs:
            docs.append("[No sources retrieved. Using model knowledge only.]")

        _progress(1, "Searching literature", "done", f"{len(docs)} sources found")
        return {"retrieved_docs": docs}

    # ── 2. Reader ─────────────────────────────
    def reader_node(state: AgentState) -> dict:
        section(2, "Reader  —  Extracting structured knowledge", _run_id)
        _progress(2, "Extracting knowledge")
        docs_text = "\n\n".join(state["retrieved_docs"])

        response = safe_llm([
            {
                "role": "system",
                "content": "You are a Research Analyst. Respond ONLY with a valid JSON object — no markdown, no commentary."
            },
            {
                "role": "user",
                "content": (
                    "Analyze the following research snippets.\n"
                    "Return a JSON object with EXACTLY these keys:\n"
                    "  - core_domain        : string\n"
                    "  - key_findings       : list of 3-5 strings\n"
                    "  - methodologies_used : list of strings\n"
                    "  - identified_gaps    : list of {type, description}\n"
                    "    type must be: limit_of_scope | conflicting_evidence | explicit_future_work\n"
                    "  - existing_papers    : list of paper titles or IDs found in snippets\n"
                    "  - novelty_score      : float 0.0-1.0\n\n"
                    f"Snippets:\n{docs_text}"
                )
            }
        ], max_tokens=1000,
           fallback='{"error": true, "raw_output": "LLM failed", "existing_papers": []}',
           config=cfg)

        parsed = extract_json(response)
        if "error" in parsed:
            print("  ⚠ JSON parse failed — using raw fallback")
            parsed = {"raw_output": response, "existing_papers": [], "error": True}
        else:
            print(f"  ✓ Domain        : {parsed.get('core_domain', 'N/A')}")
            print(f"  ✓ Novelty Score : {parsed.get('novelty_score', 'N/A')}")
            print(f"  ✓ Existing papers found: {len(parsed.get('existing_papers', []))}")

        _progress(2, "Extracting knowledge", "done")
        return {"knowledge_context": parsed}

    # ── 3. Reasoning ──────────────────────────
    def reasoning_node(state: AgentState) -> dict:
        feedback = state.get("critic_feedback", "")
        count = state.get("critique_count", 0)

        if feedback and count > 0:
            section(3, f"Reasoning  —  Refining hypothesis (attempt {count + 1})", _run_id)
            _progress(3, "Refining hypothesis")
            user_content = (
                f"Research Context:\n{json.dumps(state['knowledge_context'], indent=2)}\n\n"
                f"Your Previous Hypothesis:\n{state['final_reasoning']}\n\n"
                f"Critic Rejection Reason:\n{feedback}\n\n"
                "You MUST propose a DIFFERENT, more novel idea that is NOT covered in the "
                "existing literature. Do NOT repeat the previous hypothesis."
            )
        else:
            section(3, "Reasoning  —  Generating initial hypothesis", _run_id)
            _progress(3, "Generating hypothesis")
            user_content = (
                f"Research Context:\n{json.dumps(state['knowledge_context'], indent=2)}\n\n"
                "Propose a specific, testable, and NOVEL hypothesis that goes BEYOND "
                "what is already covered above.\n"
                "Describe: (1) Core idea  (2) Why it is novel  (3) How it can be tested."
            )

        response = safe_llm([
            {
                "role": "system",
                "content": (
                    "You are a Senior Research Scientist specialising in novel hypothesis generation. "
                    "Your hypotheses must be original and must not duplicate existing published work."
                )
            },
            {"role": "user", "content": user_content}
        ], max_tokens=1200, config=cfg)

        _progress(3, "Generating hypothesis", "done")
        return {
            "final_reasoning": response,
            "critic_feedback": "",
        }

    # ── 4. Critic — Hypothesis Novelty ────────
    def critic_node(state: AgentState) -> dict:
        section(4, "Critic  —  Checking hypothesis novelty & rigor", _run_id)
        _progress(4, "Checking novelty")
        hypothesis = state["final_reasoning"]
        context = json.dumps(state["knowledge_context"], indent=2)
        existing = state["knowledge_context"].get("existing_papers", [])

        response = safe_llm([
            {
                "role": "system",
                "content": (
                    "You are a strict peer reviewer and Research Ethics Committee member. "
                    "Ensure the hypothesis is UNIQUE, NOVEL, and not already published."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Existing Literature:\n{context}\n\n"
                    f"Known Papers: {existing}\n\n"
                    f"Proposed Hypothesis:\n{hypothesis}\n\n"
                    "Evaluate:\n"
                    "1. Is this already covered or published in the context? If YES → REJECTED\n"
                    "2. Is it scientifically rigorous and testable?\n"
                    "3. Does it offer genuine novelty?\n\n"
                    "End your response with EXACTLY one of these on its own line:\n"
                    "APPROVED  — passes all checks\n"
                    "REJECTED  — fails any check (cite specific reason)"
                )
            }
        ], max_tokens=700, fallback="APPROVED — unable to critique (LLM error)", config=cfg)

        count = state.get("critique_count", 0) + 1
        approved = is_approved(response)
        print(f"  {'✓ APPROVED' if approved else '✗ REJECTED'} (round {count})")

        _progress(4, "Checking novelty", "done", "APPROVED" if approved else "REJECTED")
        return {"critic_feedback": response, "critique_count": count}

    def check_critic(state: AgentState) -> str:
        feedback = state.get("critic_feedback", "")
        count = state.get("critique_count", 0)
        if is_approved(feedback):
            return "approved"
        if count >= 3:
            print("  ⚠ Max hypothesis iterations reached — proceeding anyway")
            _progress(4, "Checking novelty", "done", "Max iterations reached")
            return "approved"
        return "revision"

    # ── 5. Coder ──────────────────────────────
    def coder_node(state: AgentState) -> dict:
        feedback = state.get("code_feedback", "")
        count = state.get("code_critique_count", 0)

        if feedback and count > 0:
            section(5, f"Coder  —  Fixing code (attempt {count + 1})", _run_id)
            _progress(5, "Fixing experiment code")
            user_content = (
                f"Hypothesis:\n{state['final_reasoning']}\n\n"
                f"Previous Code:\n{state['generated_code']}\n\n"
                f"Execution Output / Error:\n{state['execution_output']}\n\n"
                f"Critic Feedback:\n{feedback}\n\n"
                "Fix the code. Output ONLY raw Python — no markdown fences, no explanation."
            )
        else:
            section(5, "Coder  —  Writing experiment code", _run_id)
            _progress(5, "Writing experiment code")
            user_content = (
                f"Hypothesis:\n{state['final_reasoning']}\n\n"
                "Write a clean, self-contained Python script to simulate or test this hypothesis.\n"
                "Use only standard library, numpy, or torch.\n"
                "Output ONLY raw Python — no markdown fences, no explanation."
            )

        response = safe_llm([
            {
                "role": "system",
                "content": (
                    "You are a Senior ML Engineer. "
                    "Output raw Python code only. Never use markdown fences."
                )
            },
            {"role": "user", "content": user_content}
        ], max_tokens=2000, config=cfg)

        return {
            "generated_code": strip_code_fences(response),
            "code_feedback": "",
        }

    # ── 6. Executor ───────────────────────────
    def execute_code_node(state: AgentState) -> dict:
        section(6, "Executor  —  Running experiment in HopX Sandbox", _run_id)
        _progress(6, "Running experiment")
        code = state["generated_code"]

        try:
            print("  [Sandbox] Booting HopX environment...")
            sandbox = hopx.Sandbox.create(template="base")
        except Exception as e:
            msg = f"SANDBOX_CREATE_ERROR: Could not create sandbox: {e}"
            print(f"  ✗ {msg}")
            _progress(6, "Running experiment", "error", "Sandbox creation failed")
            return {"execution_output": msg}

        try:
            print("  [Sandbox] Running experiment code...")
            result = sandbox.run_code(code)
            stdout = result.stdout.strip() if hasattr(result, 'stdout') and result.stdout else ""
            stderr = result.stderr.strip() if hasattr(result, 'stderr') and result.stderr else ""
            
            output = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
            
            if not stderr:
                print(f"  ✓ Sandbox execute success  ({len(stdout)} chars stdout)")
            else:
                preview = stderr[:300] if stderr else stdout[:300]
                print(f"  ⚠ Sandbox execute error output  —  {preview}")
        except Exception as e:
            output = f"EXECUTION FAILED: {e}"
            print(f"  ✗ Sandbox code execution failed: {e}")
        finally:
            try:
                sandbox.kill()
            except Exception:
                pass

        _progress(6, "Running experiment", "done")
        return {"execution_output": output}

    # ── 7. Code Critic ────────────────────────
    def code_critic_node(state: AgentState) -> dict:
        section(7, "Code Critic  —  Reviewing execution results", _run_id)
        _progress(7, "Reviewing code")

        response = safe_llm([
            {
                "role": "system",
                "content": "You are a Senior Software Engineer reviewing ML experiment code."
            },
            {
                "role": "user",
                "content": (
                    f"Code:\n{state['generated_code']}\n\n"
                    f"Execution Output:\n{state['execution_output']}\n\n"
                    "Evaluate:\n"
                    "1. Did it run without errors?\n"
                    "2. Did it produce meaningful, interpretable results?\n"
                    "3. Does the output actually test the hypothesis?\n\n"
                    "End with APPROVED or REJECTED (with specific fix instructions if rejected)."
                )
            }
        ], max_tokens=600, fallback="APPROVED — unable to review (LLM error)", config=cfg)

        count = state.get("code_critique_count", 0) + 1
        approved = is_approved(response)
        print(f"  {'✓ APPROVED' if approved else '✗ REJECTED'} (round {count})")

        _progress(7, "Reviewing code", "done", "APPROVED" if approved else "REJECTED")
        return {"code_feedback": response, "code_critique_count": count}

    def check_code_critic(state: AgentState) -> str:
        feedback = state.get("code_feedback", "")
        count = state.get("code_critique_count", 0)
        if is_approved(feedback):
            return "approved"
        if count >= 3:
            print("  ⚠ Max code iterations — proceeding to writer")
            _progress(7, "Reviewing code", "done", "Max iterations reached")
            return "approved"
        return "revision"

    # ── 8. Writer ─────────────────────────────
    def writer_node(state: AgentState) -> dict:
        feedback = state.get("paper_feedback", "")
        count = state.get("paper_critique_count", 0)

        if feedback and count > 0:
            section(8, f"Writer  —  Revising paper (attempt {count + 1})", _run_id)
            _progress(8, "Revising paper")
            user_content = (
                f"Previous Draft:\n{state['research_paper']}\n\n"
                f"Reviewer Feedback:\n{feedback}\n\n"
                "Revise the paper to address ALL feedback. "
                "Output the complete revised paper in Markdown."
            )
        else:
            section(8, "Writer  —  Composing research paper", _run_id)
            _progress(8, "Writing paper")
            user_content = (
                f"Research Topic: {state['research_topic']}\n\n"
                f"Related Work:\n{json.dumps(state['knowledge_context'], indent=2)}\n\n"
                f"Hypothesis & Methodology:\n{state['final_reasoning']}\n\n"
                f"Experiment Code:\n```python\n{state['generated_code']}\n```\n\n"
                f"Experimental Results:\n{state['execution_output']}\n\n"
                "Write a complete formal research paper in Markdown with sections:\n"
                "# Title\n## Abstract\n## 1. Introduction\n## 2. Related Work\n"
                "## 3. Methodology\n## 4. Experimental Setup\n## 5. Results\n"
                "## 6. Discussion\n## 7. Conclusion\n## References"
            )

        response = safe_llm([
            {
                "role": "system",
                "content": (
                    "You are an expert Scientific Writer. "
                    "Write formal, well-structured Markdown research papers."
                )
            },
            {"role": "user", "content": user_content}
        ], max_tokens=4096, config=cfg)

        word_count = len(response.split())
        print(f"  ✓ Paper draft: {word_count} words")

        _progress(8, "Writing paper", "done", f"{word_count} words")
        return {
            "research_paper": response,
            "paper_feedback": "",
        }

    # ── 9. Paper Novelty Critic ───────────────
    def paper_novelty_node(state: AgentState) -> dict:
        section(9, "Paper Critic  —  Final uniqueness & quality check", _run_id)
        _progress(9, "Final quality check")
        existing = state["knowledge_context"].get("existing_papers", [])
        sources = "\n\n".join(state["retrieved_docs"][:3])

        response = safe_llm([
            {
                "role": "system",
                "content": (
                    "You are a senior journal editor conducting a final "
                    "uniqueness and quality review."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Source Literature:\n{sources}\n\n"
                    f"Known Papers: {existing}\n\n"
                    f"Submitted Paper:\n{state['research_paper']}\n\n"
                    "Final Checks:\n"
                    "1. Does this paper duplicate any known existing work?\n"
                    "2. Is the hypothesis and contribution genuinely novel?\n"
                    "3. Is the paper well-structured and scientifically sound?\n"
                    "4. Are claims backed by experimental results?\n\n"
                    "End with APPROVED or REJECTED (with specific revision instructions if rejected)."
                )
            }
        ], max_tokens=800, fallback="APPROVED — unable to review (LLM error)", config=cfg)

        count = state.get("paper_critique_count", 0) + 1
        approved = is_approved(response)
        print(f"  {'✓ APPROVED' if approved else '✗ REJECTED'} (round {count})")

        _progress(9, "Final quality check", "done", "APPROVED" if approved else "REJECTED")
        return {"paper_feedback": response, "paper_critique_count": count}

    def check_paper_critic(state: AgentState) -> str:
        feedback = state.get("paper_feedback", "")
        count = state.get("paper_critique_count", 0)
        if is_approved(feedback):
            return "approved"
        if count >= 2:
            print("  ⚠ Max paper iterations — saving as-is")
            _progress(9, "Final quality check", "done", "Max iterations reached")
            return "approved"
        return "revision"

    # ── 10. Save Paper ────────────────────────
    def save_paper_node(state: AgentState) -> dict:
        section(10, "Save  —  Writing final paper to disk", _run_id)
        _progress(10, "Saving paper")
        os.makedirs(outputs_dir, exist_ok=True)
        base = sanitize_filename(state["research_topic"])
        md_path = os.path.join(outputs_dir, f"{base}_paper.md")
        json_path = os.path.join(outputs_dir, f"{base}_summary.json")

        from datetime import datetime, timezone

        try:
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(state["research_paper"])
            print(f"  ✓ Paper   → {md_path}")
        except OSError as e:
            print(f"  ✗ Could not write paper: {e}")

        backend = cfg.get("llm_backend", "ollama") if cfg else "ollama"
        model_name = (cfg.get("mlx_model") if backend == "mlx" else cfg.get("ollama_model")) if cfg else "unknown"

        summary = {
            "topic": state["research_topic"],
            "hypothesis": state["final_reasoning"][:500],
            "hypothesis_iterations": state.get("critique_count", 0),
            "code_iterations": state.get("code_critique_count", 0),
            "paper_iterations": state.get("paper_critique_count", 0),
            "paper_word_count": len(state.get("research_paper", "").split()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "llm_backend": backend,
            "model": model_name,
        }
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            print(f"  ✓ Summary → {json_path}")
        except OSError as e:
            print(f"  ✗ Could not write summary: {e}")

        _progress(10, "Saving paper", "done")
        return {}

    return {
        "search_node": search_node,
        "reader_node": reader_node,
        "reasoning_node": reasoning_node,
        "critic_node": critic_node,
        "check_critic": check_critic,
        "coder_node": coder_node,
        "execute_code_node": execute_code_node,
        "code_critic_node": code_critic_node,
        "check_code_critic": check_code_critic,
        "writer_node": writer_node,
        "paper_novelty_node": paper_novelty_node,
        "check_paper_critic": check_paper_critic,
        "save_paper_node": save_paper_node,
    }
