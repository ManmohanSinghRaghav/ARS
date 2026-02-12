import os
import json
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities import ArxivAPIWrapper
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from mlx_lm import load, generate

# ---------------------------
# Load MLX Model (GPU via Metal)
# ---------------------------
print("Loading MLX model...")
model, tokenizer = load("mlx-community/Qwen2.5-3B-Instruct-4bit")
print("Model loaded successfully!")

# ---------------------------
# API Key (Better: use .env file)
# ---------------------------
if "TAVILY_API_KEY" not in os.environ:
    os.environ["TAVILY_API_KEY"] = "YOUR_REAL_TAVILY_KEY"

# ---------------------------
# Agent State
# ---------------------------
class AgentState(TypedDict):
    research_topic: str
    retrieved_docs: List[str]
    knowledge_context: dict

# ---------------------------
# Reader Prompt
# ---------------------------
READER_AGENT_PROMPT = """
You are the Reader Agent for the Autonomous Research Scientist (ARS).

Analyze the provided research snippets and extract structured JSON.

Return ONLY valid JSON in this format:

{
    "core_domain": "String",
    "key_findings": ["Finding 1", "Finding 2"],
    "methodologies_used": ["Tool 1", "Algo 2"],
    "identified_gaps": [
        {
            "type": "limit_of_scope",
            "description": "..."
        },
        {
            "type": "conflicting_evidence",
            "description": "..."
        },
        {
            "type": "explicit_future_work",
            "description": "..."
        }
    ],
    "novelty_score": 0.5
}
"""

# ---------------------------
# Search Node
# ---------------------------
def search_node(state: AgentState):
    topic = state["research_topic"]
    print(f"\n[Search Agent] Searching for: {topic}")

    docs = []

    try:
        arxiv = ArxivQueryRun(
            api_wrapper=ArxivAPIWrapper(top_k_results=1, doc_content_chars_max=1000)
        )
        docs.append("ArXiv Source:\n" + arxiv.run(topic))
    except Exception as e:
        print("ArXiv error:", e)

    try:
        tavily = TavilySearchResults(k=2)
        results = tavily.invoke(topic)
        for r in results:
            docs.append(f"Web Source ({r['url']}):\n{r['content']}")
    except Exception as e:
        print("Tavily error:", e)

    return {"retrieved_docs": docs}

# ---------------------------
# Reader Node (MLX version)
# ---------------------------
def reader_node(state: AgentState):
    print("\n[Reader Agent] Analyzing with MLX...")

    docs_text = "\n\n".join(state["retrieved_docs"])

    full_prompt = f"""
{READER_AGENT_PROMPT}

Research Snippets:
{docs_text}
"""

    response = generate(
        model,
        tokenizer,
        prompt=full_prompt,
        max_tokens=800,
        temp=0.0
    )

    try:
        parsed = json.loads(response)
    except:
        parsed = {
            "error": "Model did not return valid JSON",
            "raw_output": response
        }

    return {"knowledge_context": parsed}

# ---------------------------
# Build Graph
# ---------------------------
def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("search_agent", search_node)
    workflow.add_node("reader_agent", reader_node)
    workflow.set_entry_point("search_agent")
    workflow.add_edge("search_agent", "reader_agent")
    workflow.add_edge("reader_agent", END)
    return workflow.compile()

# ---------------------------
# Main Execution
# ---------------------------
if __name__ == "__main__":
    app = build_graph()

    print("\n--- Autonomous Research Scientist (MLX Version) ---")
    topic = input("Enter research topic: ")

    if topic:
        inputs = {
            "research_topic": topic,
            "retrieved_docs": [],
            "knowledge_context": {}
        }

        result = app.invoke(inputs)

        print("\n" + "=" * 50)
        print("FINAL KNOWLEDGE CONTEXT")
        print("=" * 50)
        print(json.dumps(result["knowledge_context"], indent=2))
        print("=" * 50)
