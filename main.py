import os
import json
import re
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities import ArxivAPIWrapper
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from mlx_lm import load, generate
import mlx.core as mx

# ---------------------------
# Load MLX Model (GPU via Metal)
# ---------------------------
# This script is optimized for Apple Silicon (M-series chips)
print("--- Hardware Check ---")
try:
    device = mx.default_device()
    print(f"Current MLX Device: {device}")
except Exception as e:
    print(f"MLX Device Check Failed: {e}")

print("Loading MLX model...")
# Using the model specified in the script
# "mlx-community/Qwen2.5-3B-Instruct-bf16"
model, tokenizer = load("mlx-community/Qwen2.5-3B-Instruct-bf16")
print("Model loaded successfully!")

# ---------------------------
# API Key (Better: use .env file)
# ---------------------------
# In a real deployment, load this from .env using python-dotenv
if "TAVILY_API_KEY" not in os.environ:
    os.environ["TAVILY_API_KEY"] = ""

# ---------------------------
# State Definition
# ---------------------------
class AgentState(TypedDict):
    research_topic: str
    retrieved_docs: List[str]
    knowledge_context: dict
    final_reasoning: str
    critic_feedback: str
    critique_count: int
    generated_code: str
    execution_output: str
    code_feedback: str
    code_critique_count: int

# ---------------------------
# Helper Functions
# ---------------------------
def extract_json(text: str) -> dict:
    """Robustly extract a JSON object from model output."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
            
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
            
    return {"error": "Could not extract valid JSON", "raw_output": text}

# ---------------------------
# Nodes
# ---------------------------
def search_node(state: AgentState):
    topic = state["research_topic"]
    print(f"\n[Search Agent] Researching: {topic}")
    docs = []
    
    # ArXiv Search
    try:
        arxiv = ArxivQueryRun(api_wrapper=ArxivAPIWrapper(top_k_results=1))
        docs.append(f"ArXiv:\n{arxiv.run(topic)}")
    except Exception as e:
        print(f"ArXiv Error: {e}")

    # Tavily Web Search
    try:
        tavily = TavilySearchResults(max_results=2)
        results = tavily.invoke({"query": topic})
        if isinstance(results, list):
            for r in results:
                docs.append(f"Web ({r.get('url')}):\n{r.get('content')}")
        else:
             print(f"Tavily unexpected output: {results}")

    except Exception as e:
        print(f"Tavily Error: {e}")
        
    return {"retrieved_docs": docs}

def reader_node(state: AgentState):
    print("[Reader Agent] Analyzing and extracting JSON...")
    docs_text = "\n\n".join(state["retrieved_docs"])
    
    messages = [
        {"role": "system", "content": "Respond ONLY with a JSON object summarizing findings, gaps, and methodologies."},
        {"role": "user", "content": f"Analyze these snippets and return JSON with keys: 'core_domain', 'key_findings', 'methodologies_used', 'identified_gaps', 'novelty_score'.\n\nSnippets: {docs_text}"}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    response = generate(model, tokenizer, prompt=prompt, max_tokens=800)
    parsed = extract_json(response)
    # Check if parsed has error key and maybe retry or just accept it
    if "error" in parsed:
        print(f"[Reader Agent] Warning: Failed to parse JSON. Raw output: {parsed.get('raw_output')[:100]}...")

    return {"knowledge_context": parsed}

def reasoning_node(state: AgentState):
    print("[Reasoning Agent] Creating/Refining hypothesis...")
    knowledge_json = json.dumps(state["knowledge_context"], indent=2)
    current_feedback = state.get("critic_feedback", "")
    
    if current_feedback:
        print(f"   Refining based on feedback...")
        user_content = f"Context: {knowledge_json}\n\nPrevious Hypothesis:\n{state['final_reasoning']}\n\nCritic Feedback:\n{current_feedback}\n\nRefine the hypothesis to address the criticism."
    else:
        user_content = f"Context: {knowledge_json}\n\nFormulate a breakthrough hypothesis."

    messages = [
        {"role": "system", "content": "You are a Senior Scientist. Create a specific, testable hypothesis based on the provided research context."},
        {"role": "user", "content": user_content}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    report = generate(model, tokenizer, prompt=prompt, max_tokens=1000)
    return {"final_reasoning": report}
def critic_node(state: AgentState):
    print("[Critic Agent] Reviewing hypothesis...")
    hypothesis = state["final_reasoning"]
    
    messages = [
        {"role": "system", "content": "You are a Peer Reviewer. Critically evaluate the hypothesis for testability, novelty, and scientific rigor."},
        {"role": "user", "content": f"Hypothesis: {hypothesis}\n\nProvide a brief critique. If it is solid, end with 'APPROVED'. If it needs work, explain what is missing."}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    critique = generate(model, tokenizer, prompt=prompt, max_tokens=500)
    
    # Increment count
    count = state.get("critique_count", 0) + 1
    return {"critic_feedback": critique, "critique_count": count}
def critic_node(state: AgentState):
    print("[Critic Agent] Reviewing hypothesis...")
    hypothesis = state["final_reasoning"]
    
    messages = [
        {"role": "system", "content": "You are a Peer Reviewer. Critically evaluate the hypothesis for testability, novelty, and scientific rigor."},
        {"role": "user", "content": f"Hypothesis: {hypothesis}\n\nProvide a brief critique. If it is solid, end with 'APPROVED'. If it needs work, explain what is missing."}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    critique = generate(model, tokenizer, prompt=prompt, max_tokens=500)
    
    # Increment count
    count = state.get("critique_count", 0) + 1
    return {"critic_feedback": critique, "critique_count": count}

def coder_node(state: AgentState):
    print("[Coder Agent] Writing/Refining Python code...")
    hypothesis = state["final_reasoning"]
    code_feedback = state.get("code_feedback", "")

    if code_feedback:
        print(f"   Refining code based on feedback...")
        user_content = (f"Hypothesis: {hypothesis}\n\n"
                        f"Previous Code:\n{state['generated_code']}\n\n"
                        f"Execution Output/Error:\n{state['execution_output']}\n\n"
                        f"Critic Feedback:\n{code_feedback}\n\n"
                        f"Please fix the code. Output only the Python code block.")
    else:
         user_content = f"Hypothesis: {hypothesis}\n\nOutput only the Python code block (no markdown fences)."

    messages = [
        {"role": "system", "content": "You are an ML Engineer. Write clean, modular Python code (using standard libraries or PyTorch/NumPy) to implement a simulation or proof-of-concept for the hypothesis provided."},
        {"role": "user", "content": user_content}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    code_output = generate(model, tokenizer, prompt=prompt, max_tokens=1500)
    
    # Strip markdown if present
    code_output = re.sub(r"```python\s*", "", code_output)
    code_output = re.sub(r"```\s*", "", code_output)
    
    return {"generated_code": code_output}

def execute_code_node(state: AgentState):
    print("[Executor Agent] Saving and executing generated code...")
    code = state["generated_code"]
    
    # Save to file
    filename = "generated_experiment.py"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)
    
    print(f"Code saved to {filename}")
    
    # Execute
    try:
        # Using subprocess to run the generated script
        import subprocess
        result = subprocess.run(["python", filename], capture_output=True, text=True, timeout=60)
        output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
    except Exception as e:
        output = f"Execution failed: {str(e)}"
        
    print("Execution complete.")
    return {"execution_output": output}

def code_critic_node(state: AgentState):
    print("[Code Critic] Reviewing code execution...")
    output = state.get("execution_output", "")
    code = state.get("generated_code", "")
    
    messages = [
        {"role": "system", "content": "You are a Senior Developer. Check if the code executed successfully and produced meaningful results."},
        {"role": "user", "content": f"Code:\n{code}\n\nExecution Output:\n{output}\n\nDid this run successfully? If there are errors, explain how to fix them. If it ran but produced garbage, explain why. If it's good, say 'APPROVED'."}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    critique = generate(model, tokenizer, prompt=prompt, max_tokens=500)
    count = state.get("code_critique_count", 0) + 1
    return {"code_feedback": critique, "code_critique_count": count}

def check_code_critic(state: AgentState):
    feedback = state.get("code_feedback", "")
    count = state.get("code_critique_count", 0)
    
    if "APPROVED" in feedback.upper():
        print("   [Code Approved] Experiment Successful!")
        return "approved"
        
    if count >= 3:
        print(f"   [Code Loop Limit ({count})] Stopping...")
        return "approved"
        
    print("   [Code Revision Needed] Sending back to Coder...")
    return "revision"

# ---------------------------
# Build Graph
# ---------------------------
workflow = StateGraph(AgentState)
workflow.add_node("search_agent", search_node)
workflow.add_node("reader_agent", reader_node)
workflow.add_node("reasoning_agent", reasoning_node)
workflow.add_node("critic_node", critic_node)
workflow.add_node("coder_agent", coder_node)
workflow.add_node("executor_agent", execute_code_node)
workflow.add_node("code_critic_node", code_critic_node)

workflow.set_entry_point("search_agent")
workflow.add_edge("search_agent", "reader_agent")
workflow.add_edge("reader_agent", "reasoning_agent")
workflow.add_edge("reasoning_agent", "critic_node")

workflow.add_conditional_edges(
    "critic_node",
    check_critic,
    {
        "approved": "coder_agent",
        "revision": "reasoning_agent"
    }
)

workflow.add_edge("coder_agent", "executor_agent")
workflow.add_edge("executor_agent", "code_critic_node")

workflow.add_conditional_edges(
    "code_critic_node",
    check_code_critic,
    {
        "approved": END,
        "revision": "coder_agent"
    }
)

app = workflow.compile()

# ---------------------------
# Main Execution
# ---------------------------
if __name__ == "__main__":
    print("\n--- Autonomous Research Scientist (ARS) ---")
    topic = input("Enter research topic (or press Enter for default): ")
    if not topic.strip():
        topic = "Efficient memory management in LLMs via Sparse Attention"
    
    # Invoke app
    result = app.invoke({
        "research_topic": topic, 
        "retrieved_docs": [], 
        "knowledge_context": {}, 
        "final_reasoning": "", 
        "generated_code": "",
        "execution_output": "",
        "code_feedback": "",
        "code_critique_count": 0,
        "critique_count": 0
    })

    print("\n" + "="*60)
    print("HYPOTHESIS GENERATED")
    print("="*60)
    print(result.get("final_reasoning"))

    print("\n" + "="*60)
    print("PYTHON IMPLEMENTATION (CODER AGENT)")
    print("="*60)
    print(result.get("generated_code"))
    
    print("\n" + "="*60)
    print("EXECUTION OUTPUT")
    print("="*60)
    print(result.get("execution_output"))
    
    print("\n" + "="*60)
    print("CODE CRITIQUE (FINAL)")
    print("="*60)
    print(result.get("code_feedback"))
