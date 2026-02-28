"""
ARS — Autonomous Research Scientist
Multi-agent LangGraph pipeline: Search → Read → Hypothesise → Code → Execute → Write → Publish

Supports two LLM backends:
  • MLX   (macOS Apple Silicon — default on Darwin)
  • Ollama REST API (any platform — default on Linux / Windows)

Set LLM_BACKEND, MLX_MODEL, OLLAMA_MODEL, OLLAMA_URL in .env to override.
"""

import sys
import subprocess
import os
import json
import re
import hashlib
import platform
import traceback
from datetime import datetime, timezone
from typing import TypedDict, List

from langgraph.graph import StateGraph, END
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities import ArxivAPIWrapper
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────
load_dotenv()
os.makedirs("outputs", exist_ok=True)

TOTAL_STEPS = 10                              # for section() banners
LLM_BACKEND = os.environ.get("LLM_BACKEND", "").lower()

# Auto-detect backend when not set
if not LLM_BACKEND:
    LLM_BACKEND = "mlx" if platform.system() == "Darwin" else "ollama"

MLX_MODEL    = os.environ.get("MLX_MODEL",    "mlx-community/Qwen2.5-3B-Instruct-bf16")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_URL   = os.environ.get("OLLAMA_URL",   "http://localhost:11434")

model = None
tokenizer = None


def _boot_mlx():
    """Load MLX model + tokenizer (macOS only)."""
    global model, tokenizer
    from mlx_lm import load as mlx_load          # conditional import
    import mlx.core as mx
    try:
        device = mx.default_device()
        print(f"[HW] MLX Device : {device}")
    except Exception as e:
        print(f"[HW] MLX check failed: {e}")
    print(f"[Model] Loading {MLX_MODEL} via MLX ...")
    model, tokenizer = mlx_load(MLX_MODEL)
    print("[Model] Ready.\n")


def _boot_ollama():
    """Verify Ollama is reachable and requested model is available."""
    import requests
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        resp.raise_for_status()
        available = [m["name"] for m in resp.json().get("models", [])]
        if OLLAMA_MODEL not in available:
            # Attempt to find a partial match (e.g., "qwen2.5:3b" vs "qwen2.5:3b-instruct")
            match = [n for n in available if OLLAMA_MODEL.split(":")[0] in n]
            if not match:
                print(f"[WARN] Model '{OLLAMA_MODEL}' not found in Ollama. "
                      f"Available: {available}.  Run:  ollama pull {OLLAMA_MODEL}")
            else:
                print(f"[Model] Using closest match: {match[0]}")
        else:
            print(f"[Model] Ollama model '{OLLAMA_MODEL}' available.")
    except Exception as e:
        print(f"[WARN] Cannot reach Ollama at {OLLAMA_URL}: {e}")
        print(f"       Make sure Ollama is running:  ollama serve")
    print(f"[Model] Backend = Ollama @ {OLLAMA_URL}  model = {OLLAMA_MODEL}\n")


# ── Banner ────────────────────────────────────
print("─" * 55)
print("  ARS — Autonomous Research Scientist")
print(f"  Backend : {LLM_BACKEND.upper()}")
print("─" * 55)

if LLM_BACKEND == "mlx":
    _boot_mlx()
elif LLM_BACKEND == "ollama":
    _boot_ollama()
else:
    sys.exit(f"[ERROR] Unknown LLM_BACKEND='{LLM_BACKEND}'. Use 'mlx' or 'ollama'.")

if not os.environ.get("TAVILY_API_KEY"):
    print("[WARN] TAVILY_API_KEY not set — web search will be skipped.")

# ─────────────────────────────────────────────
# State
# ─────────────────────────────────────────────
class AgentState(TypedDict):
    # Input
    research_topic:       str
    # Search
    retrieved_docs:       List[str]
    # Reader
    knowledge_context:    dict
    # Hypothesis loop
    final_reasoning:      str
    critic_feedback:      str
    critique_count:       int
    # Code loop
    generated_code:       str
    execution_output:     str
    code_feedback:        str
    code_critique_count:  int
    # Paper loop
    research_paper:       str
    paper_feedback:       str
    paper_critique_count: int

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def section(step: int, title: str):
    """Print a consistent [N/TOTAL] banner."""
    print(f"\n{'─'*55}")
    print(f"  [{step}/{TOTAL_STEPS}]  {title}")
    print(f"{'─'*55}")


def llm(messages: list, max_tokens: int = 800) -> str:
    """Single entry point for all LLM calls — dispatches to MLX or Ollama."""
    if LLM_BACKEND == "mlx":
        from mlx_lm import generate as mlx_generate
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        return mlx_generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens)
    else:  # ollama
        import requests
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


def safe_llm(messages: list, max_tokens: int = 800, fallback: str = "") -> str:
    """Wrapper around llm() that catches errors and returns *fallback* on failure."""
    try:
        return llm(messages, max_tokens)
    except Exception as e:
        print(f"  ✗ LLM call failed: {e}")
        traceback.print_exc()
        return fallback or f"LLM_ERROR: {e}"


def extract_json(text: str) -> dict:
    """Robustly extract a JSON object from model output."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {"error": "Could not extract valid JSON", "raw_output": text}


def is_approved(feedback: str) -> bool:
    """Strict check: APPROVED must exist AND REJECTED must NOT exist."""
    f = feedback.upper()
    return "APPROVED" in f and "REJECTED" not in f


def strip_code_fences(text: str) -> str:
    text = re.sub(r"```python\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()


def sanitize_filename(name: str) -> str:
    name = name.replace(" ", "_")[:60]
    return re.sub(r'[\\/*?:"<>|]', "", name)

# ─────────────────────────────────────────────
# Nodes
# ─────────────────────────────────────────────

# ── 1. Search ─────────────────────────────────
def search_node(state: AgentState) -> dict:
    topic = state["research_topic"]
    section(1, f"Search  —  {topic}")
    docs: List[str] = []

    try:
        arxiv = ArxivQueryRun(api_wrapper=ArxivAPIWrapper(top_k_results=3))
        result = arxiv.run(topic)
        docs.append(f"[ArXiv]\n{result}")
        print("  ✓ ArXiv fetched (top 3)")
    except Exception as e:
        print(f"  ✗ ArXiv: {e}")

    try:
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

    return {"retrieved_docs": docs}


# ── 2. Reader ─────────────────────────────────
def reader_node(state: AgentState) -> dict:
    section(2, "Reader  —  Extracting structured knowledge")
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
    ], max_tokens=1000, fallback='{"error": true, "raw_output": "LLM failed", "existing_papers": []}')

    parsed = extract_json(response)
    if "error" in parsed:
        print("  ⚠ JSON parse failed — using raw fallback")
        parsed = {"raw_output": response, "existing_papers": [], "error": True}
    else:
        print(f"  ✓ Domain        : {parsed.get('core_domain', 'N/A')}")
        print(f"  ✓ Novelty Score : {parsed.get('novelty_score', 'N/A')}")
        print(f"  ✓ Existing papers found: {len(parsed.get('existing_papers', []))}")

    return {"knowledge_context": parsed}


# ── 3. Reasoning ──────────────────────────────
def reasoning_node(state: AgentState) -> dict:
    feedback = state.get("critic_feedback", "")
    count    = state.get("critique_count", 0)

    if feedback and count > 0:
        section(3, f"Reasoning  —  Refining hypothesis (attempt {count + 1})")
        user_content = (
            f"Research Context:\n{json.dumps(state['knowledge_context'], indent=2)}\n\n"
            f"Your Previous Hypothesis:\n{state['final_reasoning']}\n\n"
            f"Critic Rejection Reason:\n{feedback}\n\n"
            "You MUST propose a DIFFERENT, more novel idea that is NOT covered in the "
            "existing literature. Do NOT repeat the previous hypothesis."
        )
    else:
        section(3, "Reasoning  —  Generating initial hypothesis")
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
    ], max_tokens=1200)

    return {
        "final_reasoning": response,
        "critic_feedback": "",      # reset so stale feedback won't bleed
    }


# ── 4. Critic — Hypothesis Novelty ────────────
def critic_node(state: AgentState) -> dict:
    section(4, "Critic  —  Checking hypothesis novelty & rigor")
    hypothesis = state["final_reasoning"]
    context    = json.dumps(state["knowledge_context"], indent=2)
    existing   = state["knowledge_context"].get("existing_papers", [])

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
    ], max_tokens=700, fallback="APPROVED — unable to critique (LLM error)")

    count    = state.get("critique_count", 0) + 1
    approved = is_approved(response)
    print(f"  {'✓ APPROVED' if approved else '✗ REJECTED'} (round {count})")

    return {"critic_feedback": response, "critique_count": count}


def check_critic(state: AgentState) -> str:
    feedback = state.get("critic_feedback", "")
    count    = state.get("critique_count", 0)

    if is_approved(feedback):
        return "approved"
    if count >= 3:
        print("  ⚠ Max hypothesis iterations reached — proceeding anyway")
        return "approved"
    return "revision"


# ── 5. Coder ──────────────────────────────────
def coder_node(state: AgentState) -> dict:
    feedback = state.get("code_feedback", "")
    count    = state.get("code_critique_count", 0)

    if feedback and count > 0:
        section(5, f"Coder  —  Fixing code (attempt {count + 1})")
        user_content = (
            f"Hypothesis:\n{state['final_reasoning']}\n\n"
            f"Previous Code:\n{state['generated_code']}\n\n"
            f"Execution Output / Error:\n{state['execution_output']}\n\n"
            f"Critic Feedback:\n{feedback}\n\n"
            "Fix the code. Output ONLY raw Python — no markdown fences, no explanation."
        )
    else:
        section(5, "Coder  —  Writing experiment code")
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
    ], max_tokens=2000)

    return {
        "generated_code": strip_code_fences(response),
        "code_feedback":  "",       # reset stale feedback
    }


# ── 6. Executor ───────────────────────────────
def execute_code_node(state: AgentState) -> dict:
    section(6, "Executor  —  Running experiment")
    code     = state["generated_code"]
    filepath = os.path.join("outputs", "generated_experiment.py")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
    except OSError as e:
        msg = f"FILE_WRITE_ERROR: Could not write {filepath}: {e}"
        print(f"  ✗ {msg}")
        return {"execution_output": msg}

    try:
        proc = subprocess.run(
            [sys.executable, filepath],
            capture_output=True,
            text=True,
            timeout=120
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        output = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
        if proc.returncode == 0:
            print(f"  ✓ Exit 0  ({len(stdout)} chars stdout)")
        else:
            preview = stderr[:300] if stderr else stdout[:300]
            print(f"  ✗ Exit {proc.returncode}  —  {preview}")
    except subprocess.TimeoutExpired:
        output = "TIMEOUT: Script exceeded 120 seconds."
        print("  ✗ Timed out")
    except Exception as e:
        output = f"EXECUTION FAILED: {e}"
        print(f"  ✗ {e}")

    return {"execution_output": output}


# ── 7. Code Critic ────────────────────────────
def code_critic_node(state: AgentState) -> dict:
    section(7, "Code Critic  —  Reviewing execution results")

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
    ], max_tokens=600, fallback="APPROVED — unable to review (LLM error)")

    count    = state.get("code_critique_count", 0) + 1
    approved = is_approved(response)
    print(f"  {'✓ APPROVED' if approved else '✗ REJECTED'} (round {count})")

    return {"code_feedback": response, "code_critique_count": count}


def check_code_critic(state: AgentState) -> str:
    feedback = state.get("code_feedback", "")
    count    = state.get("code_critique_count", 0)

    if is_approved(feedback):
        return "approved"
    if count >= 3:
        print("  ⚠ Max code iterations — proceeding to writer")
        return "approved"
    return "revision"


# ── 8. Writer ─────────────────────────────────
def writer_node(state: AgentState) -> dict:
    feedback = state.get("paper_feedback", "")
    count    = state.get("paper_critique_count", 0)

    if feedback and count > 0:
        section(8, f"Writer  —  Revising paper (attempt {count + 1})")
        user_content = (
            f"Previous Draft:\n{state['research_paper']}\n\n"
            f"Reviewer Feedback:\n{feedback}\n\n"
            "Revise the paper to address ALL feedback. "
            "Output the complete revised paper in Markdown."
        )
    else:
        section(8, "Writer  —  Composing research paper")
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
    ], max_tokens=4096)

    word_count = len(response.split())
    print(f"  ✓ Paper draft: {word_count} words")

    return {
        "research_paper": response,
        "paper_feedback": "",       # reset stale feedback
    }


# ── 9. Paper Novelty Critic ───────────────────
def paper_novelty_node(state: AgentState) -> dict:
    section(9, "Paper Critic  —  Final uniqueness & quality check")
    existing = state["knowledge_context"].get("existing_papers", [])
    sources  = "\n\n".join(state["retrieved_docs"][:3])

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
    ], max_tokens=800, fallback="APPROVED — unable to review (LLM error)")

    count    = state.get("paper_critique_count", 0) + 1
    approved = is_approved(response)
    print(f"  {'✓ APPROVED' if approved else '✗ REJECTED'} (round {count})")

    return {"paper_feedback": response, "paper_critique_count": count}


def check_paper_critic(state: AgentState) -> str:
    feedback = state.get("paper_feedback", "")
    count    = state.get("paper_critique_count", 0)

    if is_approved(feedback):
        return "approved"
    if count >= 2:
        print("  ⚠ Max paper iterations — saving as-is")
        return "approved"
    return "revision"


# ── 10. Save Paper ────────────────────────────
def save_paper_node(state: AgentState) -> dict:
    section(10, "Save  —  Writing final paper to disk")
    base     = sanitize_filename(state["research_topic"])
    md_path  = os.path.join("outputs", f"{base}_paper.md")
    json_path = os.path.join("outputs", f"{base}_summary.json")

    # Save Markdown paper
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(state["research_paper"])
        print(f"  ✓ Paper   → {md_path}")
    except OSError as e:
        print(f"  ✗ Could not write paper: {e}")

    # Save JSON summary
    summary = {
        "topic":                state["research_topic"],
        "hypothesis":           state["final_reasoning"][:500],
        "hypothesis_iterations": state.get("critique_count", 0),
        "code_iterations":      state.get("code_critique_count", 0),
        "paper_iterations":     state.get("paper_critique_count", 0),
        "paper_word_count":     len(state.get("research_paper", "").split()),
        "timestamp":            datetime.now(timezone.utc).isoformat(),
        "llm_backend":          LLM_BACKEND,
        "model":                MLX_MODEL if LLM_BACKEND == "mlx" else OLLAMA_MODEL,
    }
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"  ✓ Summary → {json_path}")
    except OSError as e:
        print(f"  ✗ Could not write summary: {e}")

    return {}

# ─────────────────────────────────────────────
# Build Graph
# ─────────────────────────────────────────────
workflow = StateGraph(AgentState)

workflow.add_node("search_agent",       search_node)
workflow.add_node("reader_agent",       reader_node)
workflow.add_node("reasoning_agent",    reasoning_node)
workflow.add_node("critic_node",        critic_node)
workflow.add_node("coder_agent",        coder_node)
workflow.add_node("executor_agent",     execute_code_node)
workflow.add_node("code_critic_node",   code_critic_node)
workflow.add_node("writer_agent",       writer_node)
workflow.add_node("paper_novelty_node", paper_novelty_node)
workflow.add_node("save_paper_node",    save_paper_node)

workflow.set_entry_point("search_agent")

# Linear edges
workflow.add_edge("search_agent",    "reader_agent")
workflow.add_edge("reader_agent",    "reasoning_agent")
workflow.add_edge("reasoning_agent", "critic_node")

# Hypothesis feedback loop (max 3)
workflow.add_conditional_edges(
    "critic_node", check_critic,
    {"approved": "coder_agent", "revision": "reasoning_agent"}
)

workflow.add_edge("coder_agent",    "executor_agent")
workflow.add_edge("executor_agent", "code_critic_node")

# Code feedback loop (max 3)
workflow.add_conditional_edges(
    "code_critic_node", check_code_critic,
    {"approved": "writer_agent", "revision": "coder_agent"}
)

workflow.add_edge("writer_agent", "paper_novelty_node")

# Paper feedback loop (max 2)
workflow.add_conditional_edges(
    "paper_novelty_node", check_paper_critic,
    {"approved": "save_paper_node", "revision": "writer_agent"}
)

workflow.add_edge("save_paper_node", END)

# ─── Compile with SQLite checkpointer ─────────
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    _ckpt_path = os.path.join("outputs", "checkpoints.sqlite")
    checkpointer = SqliteSaver.from_conn_string(_ckpt_path)
    app = workflow.compile(checkpointer=checkpointer)
    print(f"[Graph] Compiled with SQLite checkpointer → {_ckpt_path}")
except ImportError:
    print("[WARN] langgraph-checkpoint-sqlite not installed — no crash recovery.")
    print("       Install it with:  pip install langgraph-checkpoint-sqlite")
    app = workflow.compile()
except Exception as e:
    print(f"[WARN] Checkpointer init failed ({e}) — running without persistence.")
    app = workflow.compile()

# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "─" * 55)
    topic = input("Enter research topic (or press Enter for default): ").strip()
    if not topic:
        topic = "Efficient memory management in LLMs via Sparse Attention"
    print(f"\nTopic: {topic}\n" + "─" * 55)

    # Deterministic thread_id for checkpointing resume
    thread_id = hashlib.md5(topic.encode()).hexdigest()[:12]
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "research_topic":       topic,
        "retrieved_docs":       [],
        "knowledge_context":    {},
        "final_reasoning":      "",
        "critic_feedback":      "",
        "critique_count":       0,
        "generated_code":       "",
        "execution_output":     "",
        "code_feedback":        "",
        "code_critique_count":  0,
        "research_paper":       "",
        "paper_feedback":       "",
        "paper_critique_count": 0,
    }

    result = app.invoke(initial_state, config=config)

    # ── Summary ───────────────────────────────
    print("\n" + "=" * 60)
    print("FINAL HYPOTHESIS")
    print("=" * 60)
    print(result.get("final_reasoning", "N/A"))

    print("\n" + "=" * 60)
    print("EXECUTION OUTPUT")
    print("=" * 60)
    print(result.get("execution_output", "N/A"))

    paper = result.get("research_paper", "")
    filename = sanitize_filename(topic) + "_paper.md"
    if paper:
        print("\n" + "=" * 60)
        print(f"RESEARCH PAPER → outputs/{filename}")
        print("=" * 60)
        print(paper[:800] + "\n\n...(see outputs/ for full paper)")
    else:
        print("\n[Writer] No paper was generated.")

    print("\n" + "─" * 55)
    print("  ARS Complete.  Check the outputs/ folder.")
    print("─" * 55)
