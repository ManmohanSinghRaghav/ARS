"""
CrewAI custom tools wrapper for ARS.
"""

import os
from crewai.tools import tool
from typing import List

from app.pipeline.runtime_context import get_tavily_api_key

# Tool 1: Literature Search (Arxiv & Tavily)
@tool("LiteratureSearchTool")
def search_literature(topic: str) -> str:
    """
    Search ArXiv and Tavily Web Search for scientific papers and articles on a specific topic.
    Always input a precise phrase representing the core topic of your research.
    """
    docs: List[str] = []
    
    # Attempt ArXiv Search
    try:
        from langchain_community.utilities import ArxivAPIWrapper
        from langchain_community.tools.arxiv.tool import ArxivQueryRun
        arxiv = ArxivQueryRun(api_wrapper=ArxivAPIWrapper(top_k_results=3))
        result = arxiv.run(topic)
        if result and "No good Arxiv Result was found" not in result:
            docs.append(f"[ArXiv Research Papers]\n{result}")
    except Exception as e:
        docs.append(f"[ArXiv Error] {e}")

    # Attempt Tavily Web Search
    tavily_key = get_tavily_api_key().strip() or os.getenv("TAVILY_API_KEY", "")
    if tavily_key:
        try:
            from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
            from langchain_community.tools.tavily_search import TavilySearchResults

            wrapper = TavilySearchAPIWrapper(tavily_api_key=tavily_key)
            tavily = TavilySearchResults(api_wrapper=wrapper, max_results=3)
            # Invoke using TavilySearchResults
            results = tavily.invoke({"query": topic})
            if isinstance(results, list):
                for r in results:
                    docs.append(f"[Web: {r.get('url', 'N/A')}]\n{r.get('content', '')}")
        except Exception as e:
            docs.append(f"[Tavily Error] {e}")
    else:
        docs.append("[Web search skipped: TAVILY_API_KEY missing]")

    if not docs:
        return "No external sources generated. Rely on internal model knowledge."
    
    return "\n\n---\n\n".join(docs)


# Tool 2: Code Execution Simulator (Modal MicroVM)
@tool("ModalSandboxTool")
def sandbox_execute(python_code: str) -> str:
    """
    Execute a python script securely inside an isolated Modal MicroVM Sandbox environment.
    Pass in python_code as completely raw multiline text string. Do not wrap in markdown quotes.
    Returns standard STDOUT or STDERR which will tell you whether or not the script succeeded or failed.
    """
    import os
    
    # Cleanup python code if agent wrapped it in markdown
    if python_code.startswith("```python"):
        python_code = python_code[9:]
    if python_code.endswith("```"):
        python_code = python_code[:-3]
    python_code = python_code.strip()
    
    # PHASE III Security: Inject Zero-Trust sys.addaudithook
    secure_prefix = """
import sys
def strict_audit_hook(event, args):
    forbidden = {'os.system', 'subprocess.Popen', 'builtins.input'}
    if event in forbidden:
        raise RuntimeError(f'SECURITY VIOLATION: Blocked event {event}')
sys.addaudithook(strict_audit_hook)
"""
    python_code = f"{secure_prefix.strip()}\n\n{python_code}"

    try:
        # Connect to Modal (requires MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in env)
        if os.getenv("MODAL_TOKEN_ID"):
            import modal
            
            # Spin up a completely ephemeral Modal Sandbox with required ML dependencies
            app = modal.App("ars-agent-sandbox")
            image = modal.Image.debian_slim().pip_install("numpy", "torch", "pandas", "scipy")
            
            # Modal Sandbox programmatic execution
            sandbox = modal.Sandbox.create(
                app=app,
                image=image,
                cmd=["python", "-c", python_code],
                timeout=120
            )
            sandbox.wait()
            
            stdout = sandbox.stdout.read()
            stderr = sandbox.stderr.read()
            
            if sandbox.returncode != 0 or stderr:
                 return f"EXPERIMENTAL RUN FAILED.\n\nReturn Code: {sandbox.returncode}\nSTDERR:\n{stderr}\n\nSTDOUT:\n{stdout}"
            return f"EXPERIMENT SUCCEEDED.\n\nSTDOUT:\n{stdout}"

        # Fallback to local process/hopx if modal keys missing
        import hopx_ai
        sandbox = hopx_ai.Sandbox.create(template="base")
        result = sandbox.run_code(python_code)
        
        stdout = result.stdout.strip() if hasattr(result, 'stdout') and result.stdout else ""
        stderr = result.stderr.strip() if hasattr(result, 'stderr') and result.stderr else ""
        
        sandbox.kill()
        
        if stderr:
             return f"EXPERIMENTAL RUN FAILED.\n\nSTDERR:\n{stderr}\n\nSTDOUT:\n{stdout}"
        
        return f"EXPERIMENT SUCCEEDED.\n\nSTDOUT:\n{stdout}"
        
    except Exception as e:
        return f"MODAL SANDBOX FATAL ERROR: {e}"
