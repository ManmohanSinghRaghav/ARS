import json
import re
from typing import Any, Dict, Optional, List


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
    # NEW: Try progressively larger substrings, don't break on first failure
    start_idx = None
    stack = []
    candidates = []  # Store all potential balanced blocks
    
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
                    candidates.append(candidate)
                    # Try to parse, if successful return immediately
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        # Continue looking for larger/more complete JSON blocks
                        continue

    # 4) If no direct JSON worked, try cleanup heuristics on the last/largest candidate
    if candidates:
        # Try from largest to smallest
        for candidate in reversed(candidates):
            # Simple single-quote -> double-quote normalization (best-effort)
            normalized = candidate.replace("\\'", "'")
            normalized = re.sub(r"(?<!\\)'", '"', normalized)
            # Reduce common escape noise
            normalized = normalized.replace('\\n', '\\n').replace('\\"', '"')
            
            try:
                return json.loads(normalized)
            except Exception:
                continue

    # 5) Last-ditch: try regex fallback to any { ... } block (greedy match)
    fallback = re.search(r'(\{[\s\S]*\})', text)
    if fallback:
        try:
            return json.loads(fallback.group(1))
        except Exception:
            # Final attempt: cleanup the greedy match
            try:
                normalized = fallback.group(1).replace("\\'", "'")
                normalized = re.sub(r"(?<!\\)'", '"', normalized)
                return json.loads(normalized)
            except Exception:
                return None
    
    return None


def extract_paper_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Specialized parser for paper JSON from CrewAI compilation task.
    More robust than generic JSON extraction for paper assembly.
    
    Handles:
    - Markdown-wrapped JSON (```json ... ```)
    - Incomplete closing braces
    - Mixed quote styles
    - LLM artifacts and explanation text
    - CrewAI output wrapping
    
    Returns a validated paper JSON dict with metadata and sections array.
    """
    if not text:
        return None
    
    text = text.strip()
    
    # Step 0: Handle CrewAI-specific wrapping (```json ... ``` inside XML-like tags)
    # Extract from ```json code fence first (highest priority for CrewAI outputs)
    md_matches = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', text, flags=re.IGNORECASE)
    for block in md_matches:
        block = block.strip()
        try:
            data = json.loads(block)
            if _validate_paper_structure(data):
                print(f"[Parser] ✅ Successfully extracted JSON from markdown fence")
                return data
        except json.JSONDecodeError:
            continue
    
    # Step 1: Try direct parse first
    try:
        data = json.loads(text)
        if _validate_paper_structure(data):
            return data
    except json.JSONDecodeError:
        pass
    
    # Step 2: Find JSON by bracket counting (more precise for paper structure)
    json_str = _find_balanced_json_for_paper(text)
    if json_str:
        try:
            data = json.loads(json_str)
            if _validate_paper_structure(data):
                print(f"[Parser] ✅ Successfully extracted JSON from balanced braces")
                return data
        except json.JSONDecodeError:
            pass
    
    # Step 3: Aggressive cleanup and normalization
    normalized = _normalize_json_string(text)
    try:
        data = json.loads(normalized)
        if _validate_paper_structure(data):
            print(f"[Parser] ✅ Successfully extracted JSON after normalization")
            return data
    except json.JSONDecodeError:
        pass
    
    # Step 4: Extract and reconstruct metadata + sections manually as last resort
    try:
        reconstructed = _reconstruct_paper_json(text)
        if reconstructed:
            print(f"[Parser] ✅ Successfully reconstructed JSON from sections")
            return reconstructed
    except Exception:
        pass
    
    print(f"[Parser] ❌ Failed to extract paper JSON - returning None")
    return None


def _validate_paper_structure(data: Any) -> bool:
    """Validate that data is a proper paper JSON structure."""
    if not isinstance(data, dict):
        return False
    
    if 'metadata' not in data or not isinstance(data['metadata'], dict):
        return False
    
    if 'sections' not in data or not isinstance(data['sections'], list):
        return False
    
    if len(data['sections']) == 0:
        return False
    
    # Validate sections
    for section in data['sections']:
        if not isinstance(section, dict):
            return False
        required_keys = {'id', 'type', 'title', 'content'}
        if not required_keys.issubset(section.keys()):
            return False
    
    return True


def _find_balanced_json_for_paper(text: str) -> Optional[str]:
    """Find the largest balanced JSON object in text.
    
    Scans forward through all '{' positions and returns the largest
    balanced JSON substring that successfully parses.
    """
    starts = [i for i, c in enumerate(text) if c == '{']
    
    best = None
    best_len = 0
    
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
            else:
                if ch == '"':
                    in_string = True
                elif ch == '{':
                    stack.append('{')
                elif ch == '}':
                    if stack:
                        stack.pop()
                        if not stack:
                            candidate = text[start:i+1]
                            if len(candidate) > best_len:
                                best = candidate
                                best_len = len(candidate)
                            break
    
    return best


def _normalize_json_string(text: str) -> str:
    """Normalize JSON string for parsing.
    
    Only performs safe transformations that won't corrupt valid JSON.
    """
    # Remove common LLM artifacts (leading non-JSON text)
    text = re.sub(r'^[^{]*', '', text)  # Remove leading non-JSON
    
    # Ensure text ends with a closing brace if missing
    # Count open vs close braces (outside strings) to decide
    stripped = text.rstrip()
    if stripped and stripped[-1] != '}':
        text = re.sub(r'[^}]*$', '}', text)
    
    # Handle common JSON errors: trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    
    # Replace single quotes with double quotes ONLY if the text
    # doesn't already contain double-quoted keys (heuristic: if no
    # '"metadata"' or '"sections"' is found, it's likely single-quoted)
    if '"metadata"' not in text and '"sections"' not in text:
        text = text.replace("\\'", "\x00")  # Protect escaped singles
        text = re.sub(r"(?<!\\)'", '"', text)
        text = text.replace("\x00", "'")  # Restore escaped singles
    
    return text


def _reconstruct_paper_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Last-resort reconstruction: manually extract metadata and sections
    from text even if JSON is malformed.
    
    Uses balanced-brace scanning to find section objects, which handles
    content with newlines, escaped quotes, and long strings that regex
    approaches cannot handle.
    """
    try:
        result = {
            "metadata": {},
            "sections": []
        }
        
        # Look for metadata fields
        title_match = re.search(r'"title"\s*:\s*"([^"]*)"', text)
        if title_match:
            result["metadata"]["title"] = title_match.group(1)
        
        author_match = re.search(r'"author"\s*:\s*"([^"]*)"', text)
        if author_match:
            result["metadata"]["author"] = author_match.group(1)
        
        date_match = re.search(r'"date"\s*:\s*"([^"]*)"', text)
        if date_match:
            result["metadata"]["date"] = date_match.group(1)
        
        institution_match = re.search(r'"institution"\s*:\s*"([^"]*)"', text)
        if institution_match:
            result["metadata"]["institution"] = institution_match.group(1)
        
        # Find section objects using balanced-brace scanning.
        # Look for objects that start with {"id" — these are section objects.
        section_starts = [m.start() for m in re.finditer(r'\{\s*"id"\s*:', text)]
        
        for start in section_starts:
            # Scan for balanced braces from this position
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
                else:
                    if ch == '"':
                        in_string = True
                    elif ch == '{':
                        stack.append('{')
                    elif ch == '}':
                        if stack:
                            stack.pop()
                            if not stack:
                                candidate = text[start:i+1]
                                try:
                                    section_obj = json.loads(candidate)
                                    if isinstance(section_obj, dict) and 'id' in section_obj:
                                        # Ensure required fields exist
                                        section_obj.setdefault('type', 'content')
                                        section_obj.setdefault('title', section_obj['id'].title())
                                        section_obj.setdefault('content', '')
                                        # Ensure content is string
                                        if not isinstance(section_obj['content'], str):
                                            section_obj['content'] = str(section_obj['content'])
                                        result["sections"].append(section_obj)
                                except json.JSONDecodeError:
                                    # Try to extract fields via regex from this block
                                    section_obj = {}
                                    id_m = re.search(r'"id"\s*:\s*"([^"]*)"', candidate)
                                    if id_m:
                                        section_obj['id'] = id_m.group(1)
                                    type_m = re.search(r'"type"\s*:\s*"([^"]*)"', candidate)
                                    if type_m:
                                        section_obj['type'] = type_m.group(1)
                                    title_m = re.search(r'"title"\s*:\s*"([^"]*)"', candidate)
                                    if title_m:
                                        section_obj['title'] = title_m.group(1)
                                    # For content, grab everything between "content": " and the last "
                                    content_m = re.search(r'"content"\s*:\s*"(.*)', candidate, re.DOTALL)
                                    if content_m:
                                        raw_content = content_m.group(1)
                                        # Strip trailing ", } etc
                                        raw_content = raw_content.rstrip().rstrip('}').rstrip().rstrip(',').rstrip().rstrip('"')
                                        section_obj['content'] = raw_content
                                    
                                    if 'id' in section_obj:
                                        section_obj.setdefault('type', 'content')
                                        section_obj.setdefault('title', section_obj['id'].title())
                                        section_obj.setdefault('content', '')
                                        result["sections"].append(section_obj)
                                break
        
        # Only return if we got some data
        if result["metadata"] and result["sections"]:
            return result
        
    except Exception:
        pass
    
    return None

