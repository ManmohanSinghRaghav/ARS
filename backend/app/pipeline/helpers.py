"""
Helper utilities extracted from original main.py.
"""

import json
import re


TOTAL_STEPS = 10


def section(step: int, title: str, run_id: int | None = None):
    """Print a consistent [N/TOTAL] banner and optionally report progress."""
    print(f"\n{'─' * 55}")
    print(f"  [{step}/{TOTAL_STEPS}]  {title}")
    print(f"{'─' * 55}")
    if run_id is not None:
        from app.pipeline.progress import add_step
        add_step(run_id, step, TOTAL_STEPS, title)


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
