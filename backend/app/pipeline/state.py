"""
AgentState TypedDict — the shared state flowing through the LangGraph pipeline.
"""

from typing import TypedDict, List


class AgentState(TypedDict):
    # Input
    research_topic: str
    # Search
    retrieved_docs: List[str]
    # Reader
    knowledge_context: dict
    # Hypothesis loop
    final_reasoning: str
    critic_feedback: str
    critique_count: int
    # Code loop
    generated_code: str
    execution_output: str
    code_feedback: str
    code_critique_count: int
    # Paper loop
    research_paper: str
    paper_feedback: str
    paper_critique_count: int
