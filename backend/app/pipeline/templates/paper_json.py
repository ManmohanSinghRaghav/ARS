"""
JSON-as-Source templates and prompts for ARS.
"""

PAPER_JSON_STRUCTURE = {
    "prompts": {
        "abstract": (
            "Write a professional abstract. "
            "Output MUST be a JSON object with keys: {'id': 'abs', 'type': 'abstract', 'title': 'Abstract', 'content': string}"
        ),
        "introduction": (
            "Write a deep introduction for the topic: {{topic}}. "
            "Output MUST be a JSON object with keys: {'id': 'intro', 'type': 'content', 'title': '1. Introduction', 'content': string}"
        ),
        "related_work": (
            "Synthesize the literature search results into a 'Related Work' section. "
            "Output MUST be a JSON object with keys: {'id': 'rw', 'type': 'content', 'title': '2. Related Work', 'content': string}"
        ),
        "methodology": (
            "Provide a rigorous Methodology. Include mathematical descriptions. "
            "Output MUST be a JSON object with keys: {'id': 'meth', 'type': 'content', 'title': '3. Methodology', 'content': string}"
        ),
        "results": (
            "Describe the experimental results. "
            "Output MUST be a JSON object with keys: {'id': 'res', 'type': 'content', 'title': '4. Experiments and Results', 'content': string}"
        ),
        "conclusion": (
            "Write the Conclusion and Discussion. "
            "Output MUST be a JSON object with keys: {'id': 'concl', 'type': 'content', 'title': '5. Conclusion', 'content': string}"
        ),
        "assembly": (
            "Combine all sections into a single 'paper_json' object. "
            "Include a 'metadata' key with 'title', 'author', 'date', and 'institution'. "
            "Include a 'sections' key which is a list of all section objects in order. "
            "Output MUST be a valid JSON object only."
        )
    }
}
