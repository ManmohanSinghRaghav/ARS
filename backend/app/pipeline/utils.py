import json
import re
from typing import Any, Dict, Optional


def _find_json_substring(text: str) -> Optional[str]:
    """Find a balanced JSON substring (object or array) in text by scanning braces/brackets.
    Returns the first valid JSON substring that parses, otherwise None.
    """
    starts = [i for i, c in enumerate(text) if c in '{[']
    for start in starts:
        stack = []
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            else:
                if ch == '"':
                    in_string = True
                    continue
                if ch in '{[':
                    stack.append(ch)
                elif ch in '}]' and stack:
                    opening = stack.pop()
                    # don't need to validate matching types strictly here; JSON parser will catch it
                if not stack:
                    candidate = text[start:i+1]
                    # Quick sanity: candidate should start with { or [
                    if candidate and candidate[0] in '{[':
                        try:
                            json.loads(candidate)
                            return candidate
                        except Exception:
                            # try next possible match
                            break
    return None


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Robustly extract the first JSON object or array found in a text string.
    Handles markdown blocks, common LLM artifacts, and nested structures by
    scanning for balanced braces/brackets and attempting to parse progressively.
    """
    if not text:
        return None

    text = text.strip()
    # 1) Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2) Fenced code block with optional json hint (```json ... ```)
    md_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, flags=re.IGNORECASE)
    if md_match:
        block = md_match.group(1).strip()
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            # fall through to further heuristics using the block as input
            text = block

    # 3) Find the first balanced JSON object using a stack scan
    start_idx = None
    stack = []
    for i, ch in enumerate(text):
        if ch == '{':
            if start_idx is None:
                start_idx = i
            stack.append('{')
        elif ch == '}':
            if stack:
                stack.pop()
                if not stack and start_idx is not None:
                    candidate = text[start_idx:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        # try cleaning below
                        break

    # 4) Heuristic cleanup: strip non-json leading/trailing, normalize quotes, collapse escapes
    candidate = text[start_idx:] if start_idx is not None else text
    candidate = re.sub(r'^[^\{]*', '', candidate)
    candidate = re.sub(r'[^\}]*$', '}', candidate)

    # Simple single-quote -> double-quote normalization (best-effort)
    normalized = candidate.replace("\\'", "'")
    normalized = re.sub(r"(?<!\\)'", '"', normalized)

    # Reduce common escape noise
    normalized = normalized.replace('\\n', '\\n').replace('\\"', '"')

    try:
        return json.loads(normalized)
    except Exception:
        # Last-ditch: try regex fallback to any { ... } block
        fallback = re.search(r'(\{[\s\S]*\})', text)
        if fallback:
            try:
                return json.loads(fallback.group(1))
            except Exception:
                return None
        return None

