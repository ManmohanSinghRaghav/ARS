"""
CrewAI custom tools wrapper for ARS.
"""

import os
import hashlib
import json
from crewai.tools import tool
from typing import List

from app.pipeline.runtime_context import get_tavily_api_key

# Optional Redis Cache
REDIS_URL = os.environ.get("REDIS_URL")
_redis_client = None
if REDIS_URL:
    try:
        import redis
        _redis_client = redis.from_url(REDIS_URL)
    except ImportError:
        pass

def _get_cache(key: str) -> str | None:
    if _redis_client:
        try:
            return _redis_client.get(key)
        except Exception:
            return None
    return None

def _set_cache(key: str, val: str):
    if _redis_client:
        try:
            _redis_client.setex(key, 86400, val) # 1 day cache
        except Exception:
            pass

# Tool 1: Literature Search (Arxiv & Tavily)
@tool("LiteratureSearchTool")
def search_literature(topic: str) -> str:
    """
    Search ArXiv and Tavily Web Search for scientific papers and articles on a specific topic.
    Always input a precise phrase representing the core topic of your research.
    """
    
    # Check cache
    cache_key = f"search_cache:{hashlib.md5(topic.encode('utf-8')).hexdigest()}"
    cached_val = _get_cache(cache_key)
    if cached_val:
        return cached_val.decode('utf-8') if isinstance(cached_val, bytes) else cached_val

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
        result_str = "No external sources generated. Rely on internal model knowledge."
    else:
        result_str = "\n\n---\n\n".join(docs)
        
    _set_cache(cache_key, result_str)
    return result_str


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
        if not os.getenv("MODAL_TOKEN_ID") or not os.getenv("MODAL_TOKEN_SECRET"):
            return "EXPERIMENTAL RUN FAILED.\n\nModal Sandbox is not configured. Please set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in the environment to enable secure code execution."

        import modal
        
        # Spin up a completely ephemeral Modal Sandbox with required ML dependencies
        app = modal.App.lookup("ars-agent-sandbox", create_if_missing=True)
        image = modal.Image.debian_slim().pip_install("numpy", "torch", "pandas", "scipy")
        
        # Modal Sandbox programmatic execution
        sandbox = modal.Sandbox.create(
            "python", "-c", python_code,
            app=app,
            image=image,
            timeout=120
        )
        sandbox.wait()
        
        stdout = sandbox.stdout.read()
        stderr = sandbox.stderr.read()
        
        if sandbox.returncode != 0 or stderr:
             return f"EXPERIMENTAL RUN FAILED.\n\nReturn Code: {sandbox.returncode}\nSTDERR:\n{stderr}\n\nSTDOUT:\n{stdout}"
        return f"EXPERIMENT SUCCEEDED.\n\nSTDOUT:\n{stdout}"

    except Exception as e:
        return f"MODAL SANDBOX FATAL ERROR: {e}"
