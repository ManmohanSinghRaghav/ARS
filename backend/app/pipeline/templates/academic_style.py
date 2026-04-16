"""
Academic style templates and few-shot examples for paper generation.
Inspired by HKUDS/AI-Researcher.
"""

NEURIPS_STYLE = {
    "sections": [
        "Abstract",
        "1 Introduction",
        "2 Related Work",
        "3 Methodology",
        "4 Experiments",
        "5 Conclusion",
        "References"
    ],
    "formatting_rules": [
        "Use LaTeX syntax for all mathematical formulas (e.g., $E=mc^2$).",
        "Use formal academic tone (passive voice where appropriate, avoidance of contractions).",
        "Ensure every major claim is grounded in either a reference or an experimental result.",
    ],
    "methodology_prompt": """
Write the 'Methodology' section for the research paper. 
Focus on technical clarity. Define notations early. 
Include at least one LaTeX formalization of the core algorithm.
Structure:
- 3.1 Problem Formulation
- 3.2 Proposed Architecture
- 3.3 Theoretical Integration
""",
    "results_prompt": """
Write the 'Experiments' section for the research paper.
Use the provided JSON Result Card to generate factual statements.
Embed the following LaTeX table structure:
{{latex_table}}
Structure:
- 4.1 Dataset & Experimental Setup
- 4.2 Main Results
- 4.3 Discussion of Findings
"""
}

VIBE_TEMPLATES = {
    "Deep Academic": NEURIPS_STYLE,
    "Fast-Paced Prototype": {
        "sections": ["Abstract", "The Idea", "Implementation", "Initial Results", "Next Steps"],
        "formatting_rules": ["Keep it concise", "Focus on results over theory"],
    }
}
