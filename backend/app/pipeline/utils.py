import json
import re
from typing import Any, Dict, Optional

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Robustly extract the first JSON object found in a text string.
    Handles markdown blocks and conversational filler.
    """
    try:
        # 1. Try direct parse
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try finding JSON inside markdown blocks or braces
    # Look for the first { and the last }
    match = re.search(r'(\{[\s\S]*\})', text)
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 3. Last ditch: try cleaning up common LLM artifacts
            # (Remove common trailing characters that might break JSON)
            cleaned = re.sub(r'^[^{]*', '', json_str)
            cleaned = re.sub(r'[^}]*$', '', cleaned)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return None
    return None
