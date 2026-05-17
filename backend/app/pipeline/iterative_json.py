"""
Iterative JSON Completion System for CrewAI.
Handles incomplete JSON by requesting additional iterations from the writer agent.
Combines multiple JSON fragments into a complete, valid structure.
"""

import json
import re
from typing import Dict, Any, Optional, List, Tuple


def is_json_complete(text: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if text contains a complete, valid JSON object.
    
    Returns:
        (is_complete: bool, parsed_data: dict or None)
    """
    text = text.strip()
    try:
        # Try direct parse
        data = json.loads(text)
        if isinstance(data, dict) and "metadata" in data and "sections" in data:
            return True, data
    except json.JSONDecodeError:
        pass
    
    # Check for markdown-wrapped JSON
    md_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, flags=re.IGNORECASE)
    if md_match:
        try:
            data = json.loads(md_match.group(1))
            if isinstance(data, dict) and "metadata" in data and "sections" in data:
                return True, data
        except json.JSONDecodeError:
            pass
    
    # Fallback: try the robust paper JSON parser (handles explanation text wrapping)
    try:
        from app.pipeline.utils import extract_paper_json
        data = extract_paper_json(text)
        if data and isinstance(data, dict) and "metadata" in data and "sections" in data:
            sections = data.get("sections", [])
            # Consider it complete only if it has at least 3 sections
            # (abstract + intro + at least one more)
            if len(sections) >= 3:
                return True, data
            # Even partial results are useful — return them but as incomplete
            return False, data
    except Exception:
        pass
    
    return False, None


def extract_last_valid_section(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract the last valid/complete section object from incomplete JSON.
    Used to identify where the JSON was cut off.
    
    Example: If "sections": [..., {"id": "intro", ...}, {"id": "meth", "type": "content", "title": "3. Methodology", "content": "content here
    Will extract the last complete section object.
    """
    # Find all section-like objects in the text
    section_pattern = r'\{\s*"id"\s*:\s*"([^"]*)"[^}]*?"type"\s*:\s*"([^"]*)"[^}]*?"title"\s*:\s*"([^"]*)"[^}]*?"content"\s*:\s*"((?:[^"\\]|\\.)*)"[^}]*\}'
    
    matches = list(re.finditer(section_pattern, text, re.DOTALL))
    if matches:
        last_match = matches[-1]
        section_id, section_type, section_title, section_content = last_match.groups()
        return {
            "id": section_id,
            "type": section_type,
            "title": section_title,
            "content": section_content,
            "position": last_match.end()  # Where this section ends
        }
    
    return None


def identify_missing_sections(parsed_json: Dict[str, Any], all_sections: List[str]) -> List[str]:
    """
    Identify which sections are missing from the parsed JSON.
    
    Args:
        parsed_json: The partially parsed paper JSON
        all_sections: List of all expected section IDs ('abs', 'intro', 'rw', 'meth', 'res', 'concl')
    
    Returns:
        List of missing section IDs
    """
    if not parsed_json or "sections" not in parsed_json:
        return all_sections
    
    present_ids = {s.get("id") for s in parsed_json.get("sections", [])}
    return [sid for sid in all_sections if sid not in present_ids]


def merge_json_fragments(fragments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge multiple JSON fragments (from iterations) into a single complete JSON.
    
    Strategy:
    1. Take metadata from first fragment (most likely to be complete)
    2. Combine all sections from all fragments
    3. Remove duplicates based on section ID
    4. Order sections correctly (abs, intro, rw, meth, res, concl)
    
    Args:
        fragments: List of parsed JSON dicts from multiple iterations
    
    Returns:
        Complete merged JSON
    """
    if not fragments:
        return None
    
    merged = {
        "metadata": fragments[0].get("metadata", {}),
        "sections": []
    }
    
    # Collect all sections from all fragments
    section_map = {}  # Use section ID as key to avoid duplicates
    for fragment in fragments:
        for section in fragment.get("sections", []):
            section_id = section.get("id")
            if section_id:
                # Prefer longer content (more complete)
                if section_id not in section_map or len(section.get("content", "")) > len(section_map[section_id].get("content", "")):
                    section_map[section_id] = section
    
    # Order sections in standard academic paper order
    section_order = ["abs", "intro", "rw", "meth", "res", "concl"]
    for section_id in section_order:
        if section_id in section_map:
            merged["sections"].append(section_map[section_id])
    
    # Add any other sections not in standard order
    for section_id, section in section_map.items():
        if section_id not in section_order:
            merged["sections"].append(section)
    
    return merged


def create_continuation_prompt(last_section: Dict[str, Any], missing_sections: List[str]) -> str:
    """
    Create a prompt asking the writer to continue from where it left off.
    
    Args:
        last_section: The last complete section that was extracted
        missing_sections: List of section IDs that need to be generated
    
    Returns:
        String prompt for the agent
    """
    missing_text = ", ".join(f"'{s}'" for s in missing_sections)
    
    prompt = f"""The previous response was incomplete. You generated the '{last_section['id']}' section, but the JSON was cut off.

Please continue and generate the remaining sections: {missing_text}

Important: 
1. Do NOT regenerate the '{last_section['id']}' section again
2. Continue ONLY with the missing sections
3. Output a COMPLETE, valid JSON object with:
   - The same 'metadata' from before
   - A 'sections' array with ALL sections (including the previously generated ones we'll combine later)
4. Ensure each section has: 'id', 'type', 'title', 'content'
5. Output ONLY valid JSON, no explanation text

Example structure:
{{
    "metadata": {{"title": "...", "author": "...", "date": "...", "institution": "..."}},
    "sections": [
        {{"id": "abs", "type": "abstract", "title": "Abstract", "content": "..."}},
        {{"id": "intro", "type": "content", "title": "1. Introduction", "content": "..."}},
        ...additional sections...
    ]
}}"""
    
    return prompt


class IterativeJSONBuilder:
    """
    Manages iterative JSON building with automatic continuation on incomplete output.
    """
    
    def __init__(self, max_iterations: int = 3):
        """
        Args:
            max_iterations: Maximum number of iterations to attempt
        """
        self.max_iterations = max_iterations
        self.iterations: List[Dict[str, Any]] = []
        self.completed = False
    
    def add_iteration(self, output: str) -> Tuple[bool, Optional[str]]:
        """
        Process a new iteration output.
        
        Args:
            output: The raw output from the LLM
        
        Returns:
            (is_complete: bool, continuation_prompt: str or None)
            - If complete: (True, None)
            - If incomplete: (False, "prompt for next iteration")
        """
        is_complete, parsed = is_json_complete(output)
        
        if is_complete:
            self.iterations.append(parsed)
            self.completed = True
            return True, None
        
        # JSON is incomplete - extract what we have and plan continuation
        if parsed:
            # Partial JSON was parsed successfully
            self.iterations.append(parsed)
        else:
            # Try to extract any sections from the raw output
            from app.pipeline.utils import extract_paper_json
            parsed = extract_paper_json(output)
            if parsed:
                self.iterations.append(parsed)
        
        # Identify what's missing
        if self.iterations:
            all_sections = ["abs", "intro", "rw", "meth", "res", "concl"]
            missing = identify_missing_sections(self.iterations[-1], all_sections)
            
            if missing and len(self.iterations) < self.max_iterations:
                last_section = extract_last_valid_section(output)
                continuation_prompt = create_continuation_prompt(
                    last_section or {"id": "unknown"},
                    missing
                )
                return False, continuation_prompt
        
        return False, None
    
    def finalize(self) -> Optional[Dict[str, Any]]:
        """
        Finalize and merge all iterations into a single complete JSON.
        
        Returns:
            Complete merged JSON or None if no iterations were collected
        """
        if not self.iterations:
            return None
        
        if len(self.iterations) == 1:
            return self.iterations[0]
        
        # Merge multiple iterations
        merged = merge_json_fragments(self.iterations)
        self.completed = True
        return merged
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the builder."""
        return {
            "iterations": len(self.iterations),
            "completed": self.completed,
            "sections": sum(len(it.get("sections", [])) for it in self.iterations),
            "total_content_chars": sum(
                sum(len(s.get("content", "")) for s in it.get("sections", []))
                for it in self.iterations
            )
        }
