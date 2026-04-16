"""
CrewAI Orchestration pipeline.
Replaces LangChain/LangGraph completely.
Integrates ChromaDB RAG for grounding span indexing and semantic retrieval.
"""
import os
import json
import litellm
from crewai import Agent, Task, Crew, Process
from app.config import get_settings
from app.pipeline.tools import search_literature, sandbox_execute, retrieve_grounding_spans_tool
from app.pipeline.llm_factory import get_tier_llm
from app.pipeline.progress import add_step
from app.pipeline.rag import index_grounding_spans, clear_run_spans
from app.pipeline.result_extractor import extract_results_from_output
from app.pipeline.templates.latex_base import LATEX_TEMPLATE, NEURIPS_LATEX_STYLE

# --- Initialize Global LLM API Caching ---
_settings = get_settings()
redis_url = (_settings.REDIS_URL or "").strip() or os.environ.get("REDIS_URL")
if redis_url:
    try:
        litellm.cache = litellm.Cache(type="redis", url=redis_url)
        print("[CrewAI] Redis LLM Cache enabled.")
    except Exception as e:
        print(f"[CrewAI] Redis initialization failed: {e}. Falling back to default.")
else:
    litellm.cache = litellm.Cache(type="disk")
    print("[CrewAI] Disk LLM Cache enabled.")

def run_crew_pipeline(topic: str, run_id: str, llm_config: dict | None = None) -> dict:
    """
    Builds the CrewAI agents and tasks, then kicks off the pipeline.
    Returns a dictionary of artifacts (generated code, reasoning, paper).
    """

    # Vibe and Input mapping for Agentic Intent Architecture
    target_vibe = llm_config.get("vibe", "Deep Academic") if llm_config else "Deep Academic"
    user_commands = llm_config.get("commands", "") if llm_config else ""
    
    # Tiered LLMs
    reasoning_llm = get_tier_llm("reasoning", llm_config)
    extraction_llm = get_tier_llm("extraction", llm_config)
    critic_llm = get_tier_llm("critic", llm_config)

    # Helper function to report to UI
    def _progress(step: int, title: str, status: str = "running", detail: str = ""):
        # Total steps in modular pipeline is roughly 12 (including writing segments)
        add_step(run_id, step, 12, title, status, detail)
        print(f"[CrewAI] Step {step}/12 - {title}")

    # ==========================================
    # AGENTS (v3.1 Architecture)
    # ==========================================
    researcher = Agent(
        role="Principal Literature Researcher",
        goal=f"Mines concise structured Grounding Spans and latest papers about: {topic}",
        backstory=(
            "You are an expert AI literature parsing engine. "
            "You MUST ONLY use the 'LiteratureSearchTool' for discovery. Do not attempt to use any other search tool names. "
            "Answer only with essential verbatim evidence and metadata. "
            "Do not include the full tool output in your reasoning; instead summarize and extract exact grounding spans. "
            "Identify missing knowledge edges while keeping the prompt size minimal."
        ),
        llm=extraction_llm,
        tools=[search_literature],
        allow_delegation=False,
        verbose=True,
    )

    lead_scientist = Agent(
        role="Lead Research Scientist",
        goal="Synthesize structured observations into a novel, falsifiable scientific hypothesis using RetrieveGroundingSpansTool.",
        backstory=(
            f"You are a visionary intent architect operating in a '{target_vibe}' vibe. "
            "You MUST use the RetrieveGroundingSpansTool to search extracted literature to formulate breakthrough testable claims. "
            "Hypotheses must explicitly define variable relationships measurable via code."
        ),
        llm=reasoning_llm,
        tools=[retrieve_grounding_spans_tool],
        allow_delegation=False,
        verbose=True,
    )

    ml_engineer = Agent(
        role="Machine Learning Simulation Engineer",
        goal="Autonomously write and validate analytical code within a secure modal microVM/sandbox.",
        backstory=(
            "You are a senior simulation engineer. "
            "You MUST use your SandboxTool to execute the code. "
            "If code fails, you perform the 'Karpathy Move': ingest the stack trace and self-correct once! "
            "You can also use RetrieveGroundingSpansTool if you need algorithm details from literature."
        ),
        llm=reasoning_llm,
        tools=[sandbox_execute, retrieve_grounding_spans_tool],
        allow_delegation=False,
        verbose=True,
    )

    verifier = Agent(
        role="Adversarial RefLens Critic",
        goal="Check hallucinated citations and logically dissect experimental claims using specific tool retrieval.",
        backstory=(
            "You act as the 'Verifier'. You decompose synthesis into 'Atomic Claims' and perform Multi-Hop Tracing. "
            "You MUST use the RetrieveGroundingSpansTool to find evidence for claims from the ChromaDB index. "
            "Any claim lacking strict verbatim evidence is marked 'Speculative'."
        ),
        llm=critic_llm,
        tools=[retrieve_grounding_spans_tool],
        allow_delegation=False,
        verbose=True,
    )

    academic_writer = Agent(
        role="Senior Academic Publisher (LaTeX Expert)",
        goal=f"Draft a formal, publication-ready research paper in professional LaTeX with high technical depth.",
        backstory=(
            "You weave verified claims and experimental results into beautiful, rigorous LaTeX documents. "
            "You MUST use LaTeX environments for sections, math, algorithms, and tables. "
            "You follow a deep multi-stage writing strategy to ensure large, comprehensive manuscripts."
        ),
        llm=reasoning_llm,
        tools=[retrieve_grounding_spans_tool],
        allow_delegation=False,
        verbose=True,
    )

    # ==========================================
    # TASKS (Turbo Pipeline)
    # ==========================================
    
    task_research = Task(
        description=f"Parse the research topic: '{topic}'. Keep these sub-commands in mind: {user_commands}. Use tools to mine ArXiv/Web, but keep all citations concise and only extract exact grounding spans and metadata.",
        expected_output="A structured output mapping 3 major gaps and verbatim grounding spans extracted from literature.",
        agent=researcher,
        async_execution=False
    )

    task_hypothesis = Task(
        description=f"Use RetrieveGroundingSpansTool to query the researcher's extracted spans with user constraints: {user_commands}. Formulate a SINGLE falsifiable hypothesis using System 2 reasoning.",
        expected_output="A mathematically or computationally testable hypothesis statement, justifying novelty.",
        agent=lead_scientist,
        context=[],  # Refactored for RAG Tool
        async_execution=False
    )

    task_experiment = Task(
        description="Write an E2B/Modal sandbox Python script testing the hypothesis. Use RetrieveGroundingSpansTool if you need algorithm details. Execute it. If it fails, read STDERR, do the 'Karpathy Move' and fix it.",
        expected_output="The final working Python code, along with stdout metrics proving/disproving the claim.",
        agent=ml_engineer,
        context=[task_hypothesis],
        async_execution=False
    )

    task_verify = Task(
        description="Verify the experiment outputs and hypothesis claims using RetrieveGroundingSpansTool. Output MUST be a STRICT JSON array of objects with keys: {'claim': string, 'evidence_span': string, 'status': 'Verified' | 'Speculative'}.",
        expected_output="A JSON array of formal 'Grounding Card' objects mapping each atomic claim to verbatim quotes. If confidence < 90%, mark 'Speculative'.",
        agent=verifier,
        context=[task_hypothesis, task_experiment],
        async_execution=False  # Gating synchronization point
    )

    # --- Extraction Component (POST Experiment) ---
    result_card = {}
    def task_experiment_cb(task_output):
        nonlocal result_card
        _progress(6, "Sandbox Execution: Karpathy Move complete", "done")
        try:
            result_card = extract_results_from_output(task_output.raw)
            print(f"[CrewAI] Extracted Result Card: {json.dumps(result_card, indent=2)}")
        except Exception as e:
            print(f"[CrewAI] Warning: Result extraction failed: {e}")
    task_experiment.callback = task_experiment_cb

    # --- Modular Writing Tasks (DEEP SEQUENTIAL) ---
    prompts = NEURIPS_LATEX_STYLE["prompts"]
    
    task_intro = Task(
        description=prompts["introduction"].replace("{{topic}}", topic),
        expected_output="A deep, multi-paragraph LaTeX Introduction section.",
        agent=academic_writer,
        context=[task_research, task_hypothesis],
        async_execution=False
    )

    task_rw = Task(
        description=prompts["related_work"],
        expected_output="A comprehensive LaTeX Related Work section.",
        agent=academic_writer,
        context=[task_research],
        async_execution=False
    )

    task_methodology = Task(
        description=prompts["methodology"],
        expected_output="A rigorous LaTeX Methodology section with formulas and algorithm environments.",
        agent=academic_writer,
        context=[task_hypothesis, task_experiment],
        async_execution=False
    )

    task_results = Task(
        description=prompts["results"].replace("{{latex_table}}", result_card.get("latex_table", "N/A")),
        expected_output="The Experiments and Results section in professional LaTeX.",
        agent=academic_writer,
        context=[task_experiment, task_verify],
        async_execution=False
    )

    task_conclusion = Task(
        description=prompts["conclusion"],
        expected_output="LaTeX Conclusion and Discussion sections.",
        agent=academic_writer,
        context=[task_intro, task_methodology, task_results],
        async_execution=False
    )

    task_abstract = Task(
        description="Synthesize the findings into a high-impact LaTeX Abstract.",
        expected_output="A professional LaTeX Abstract.",
        agent=academic_writer,
        context=[task_intro, task_methodology, task_results],
        async_execution=False
    )

    # FINAL ASSEMBLY TASK
    task_compilation = Task(
        description=(
            "Combine all sections into a single valid LaTeX document using the predefined structure. "
            "Ensure all packages mentioned in the prompt are correctly used. "
            "The final output must be exactly what goes between \\begin{document} and \\end{document}, "
            "preserving the hierarchical sectioning."
        ),
        expected_output="A complete, professional LaTeX string representing the paper body.",
        agent=academic_writer,
        context=[task_abstract, task_intro, task_rw, task_methodology, task_results, task_conclusion],
        async_execution=False
    )

    def task_research_cb(task_output): 
        # Attempt to index chunks
        try:
            raw_text = task_output.raw
            # Split roughly by paragraphs or sentences
            chunks = raw_text.split('\n\n')
            spans = []
            for chunk in chunks:
                if len(chunk.strip()) > 30:
                    spans.append({"text": chunk, "source": "Literature Review Extraction"})
            if spans:
                index_grounding_spans(run_id, topic, spans)
        except Exception as e:
            print(f"[RAG] Failed to extract indexed chunks: {e}")
            
        _progress(2, "Extraction Engine Completed (Grounding Spans Mined)", "done")
    task_research.callback = task_research_cb

    def task_hypothesis_cb(*args): _progress(4, "Reasoning Core: Hypothesis Proposed", "done")
    task_hypothesis.callback = task_hypothesis_cb

    # Corrected callback for experiment to use our internal logic
    # (already handled in methodology task setup above via nonlocal result_card)

    def task_verify_cb(*args):
        # Validate hallucination threshold
        try:
            val = task_verify.output.raw
            parsed = json.loads(val[val.find('['):val.rfind(']')+1])
            speculative_ops = sum(1 for c in parsed if c.get('status') == 'Speculative')
            if speculative_ops > len(parsed) / 2:
                 _progress(8, f"Adversarial Critic: Tracing failed. High Speculative claims ({speculative_ops}). Halt triggered.", "error")
                 raise ValueError("Adversarial Verifier Halt: Hallucination ratio exceeded > 50%. Reflexion required.")
            _progress(8, "Adversarial Critic: RefLens Verification Passed", "done")
        except json.JSONDecodeError:
            _progress(8, "Adversarial Critic: JSON parse error during verification.", "done")
            
    task_verify.callback = task_verify_cb

    def task_compilation_cb(*args): _progress(12, "Final Manuscript Compiled & Synchronized", "done")
    task_compilation.callback = task_compilation_cb

    # ==========================================
    # CREW
    # ==========================================
    
    _progress(1, "Orchestrating agents via Real-Time Router...")
    crew = Crew(
        agents=[researcher, lead_scientist, ml_engineer, verifier, academic_writer],
        tasks=[
            task_research, task_hypothesis, task_experiment, task_verify, 
            task_intro, task_rw, task_methodology, task_results, task_conclusion, task_abstract, task_compilation
        ],
        process=Process.sequential,
        verbose=True
    )

    print("[CrewAI] Kicking off Deep LaTeX Lifecycle...")
    try:
        final_body = crew.kickoff()
    except Exception as e:
        print(f"[CrewAI] Reflexion Error: {e}")
        raise e

    # Assemble the full LaTeX document
    final_latex = LATEX_TEMPLATE.replace("[[TITLE]]", topic.title())
    final_latex = final_latex.replace("[[ABSTRACT]]", str(task_abstract.output.raw if task_abstract.output else "N/A"))
    final_latex = final_latex.replace("[[CONTENT]]", str(final_body))
    final_latex = final_latex.replace("[[REFERENCES]]", "No external references provided.") # Placeholder

    # Summary formatting (RefLens Grounding extraction)
    summary_data = {}
    try:
        if task_verify.output and task_verify.output.raw:
            raw_vid = task_verify.output.raw
            json_block = raw_vid[raw_vid.find('['):raw_vid.rfind(']')+1]
            if json_block:
                summary_data = {"grounding": json.loads(json_block)}
            else:
                 summary_data = {"grounding": json.loads(raw_vid)}
    except:
        summary_data = {"grounding": task_verify.output.raw if task_verify.output else "FAILED JSON PARSE"}

    # Index grounding spans into ChromaDB for semantic retrieval and verification
    try:
        if task_verify.output and task_verify.output.raw:
            raw_vid = task_verify.output.raw
            json_block = raw_vid[raw_vid.find('['):raw_vid.rfind(']')+1]
            if json_block:
                grounding_cards = json.loads(json_block)
                # Extract spans from grounding cards
                grounding_spans = [
                    {
                        "text": card.get("evidence_span", ""),
                        "source": card.get("claim", ""),
                        "url": ""
                    }
                    for card in grounding_cards if isinstance(card, dict) and card.get("evidence_span")
                ]
                if grounding_spans:
                    index_grounding_spans(run_id, topic, grounding_spans)
                    print(f"[CrewAI] Indexed {len(grounding_spans)} grounding spans into ChromaDB")
    except Exception as e:
        print(f"[CrewAI] Warning: Failed to index grounding spans: {e}")

    # Cleanup DB: Free vector storage after run is done to avoid bloating Chroma
    # clear_run_spans(run_id)

    return {
        "final_paper": final_latex,
        "hypothesis": str(task_hypothesis.output.raw if task_hypothesis.output else "N/A"),
        "execution_output": str(task_experiment.output.raw if task_experiment.output else "N/A"),
        "retrieved_docs": str(task_research.output.raw if task_research.output else "N/A"),
        "summary_data": summary_data
    }

def refine_paper(original_paper_id: str, feedback: str, run_id: str, db, llm_config: dict | None = None) -> str:
    """
    Triggers a secondary pipeline to refine an existing research paper based on user feedback.
    """
    doc = db.collection("runs").document(original_paper_id).get()
    if not doc.exists:
        raise ValueError("Original run not found")
    
    run_data = doc.to_dict()
    topic = run_data.get("topic", "Unknown")
    original_paper = run_data.get("paper_markdown", "")
    
    reasoning_llm = get_tier_llm("reasoning", llm_config)
    
    academic_refiner = Agent(
        role="Senior Peer Reviewer & Editor",
        goal=f"Rewrite and improve the research paper based on the feedback: {feedback}",
        backstory=(
            "You are a meticulous editor. You take an existing manuscript and refine it "
            "to address specific critiques while maintaining academic rigor and LaTeX formatting."
        ),
        llm=reasoning_llm,
        allow_delegation=False,
        verbose=True,
    )

    task_refine = Task(
        description=(
            f"Original Paper Topic: {topic}\n"
            f"Feedback: {feedback}\n\n"
            f"Original Content:\n{original_paper}\n\n"
            "Please rewrite the parts of the paper relevant to the feedback. "
            "Ensure the final output is a complete, well-structured professional LaTeX paper."
        ),
        expected_output="The complete refined research paper in professional LaTeX.",
        agent=academic_refiner,
        async_execution=False
    )

    crew = Crew(
        agents=[academic_refiner],
        tasks=[task_refine],
        process=Process.sequential,
        verbose=True
    )

    print(f"[CrewAI] Kicking off Refinement Loop for {run_id}...")
    refined_paper = crew.kickoff()
    
    return str(refined_paper)
