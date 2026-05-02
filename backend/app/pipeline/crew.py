"""
CrewAI Orchestration pipeline.
Replaces LangChain/LangGraph completely.
Integrates ChromaDB RAG for grounding span indexing and semantic retrieval.
"""
import os
import json
import litellm
from crewai import Agent, Task, Crew, Process
from crewai.tasks.task_output import TaskOutput
from app.config import get_settings
from app.pipeline.tools import search_literature, sandbox_execute, retrieve_grounding_spans_tool
from app.pipeline.llm_factory import get_tier_llm
from app.pipeline.progress import add_step, get_completed_tasks
from app.pipeline.rag import index_grounding_spans, clear_run_spans
from app.pipeline.result_extractor import extract_results_from_output
from app.pipeline.templates.paper_json import PAPER_JSON_STRUCTURE

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
    def _progress(step: int, title: str, status: str = "running", detail: str = "", output: str = "", is_internal: bool = False):
        # Total steps in modular pipeline (unique step numbers for resume-safe progress)
        add_step(run_id, step, 15, title, status, detail, output, is_internal=is_internal)
        print(f"[CrewAI] Step {step}/15 - {title}")

    # Load previously completed tasks for resumption
    completed_tasks = get_completed_tasks(run_id)
    print(f"[CrewAI] Resumption Check: Found {len(completed_tasks)} completed tasks.")

    # --- Execution Mode Logic ---
    execution_enabled = (llm_config or {}).get("execution_enabled", True)

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
        goal="Autonomously write and validate analytical code" + (" within a secure modal microVM/sandbox." if execution_enabled else " via rigorous theoretical derivation."),
        backstory=(
            "You are a senior simulation engineer. "
            + ("You MUST use your SandboxTool to execute the code. If code fails, you perform the 'Karpathy Move': ingest the stack trace and self-correct once! "
               "You can also use RetrieveGroundingSpansTool if you need algorithm details from literature."
               if execution_enabled else
               "You operate in THEORETICAL MODE. Derive results via mathematical logic and proof. "
               "You have access to retrieved literature context from prior tasks — use it directly without calling any tools.")
        ),
        llm=reasoning_llm,
        tools=([sandbox_execute, retrieve_grounding_spans_tool] if execution_enabled else []),
        allow_delegation=False,
        verbose=True,
    )

    verifier = Agent(
        role="Adversarial RefLens Critic",
        goal="Decompose research claims into atomic statements and map each to verbatim evidence from the research context.",
        backstory=(
            "You act as the 'Verifier'. You receive a summary of the literature and experimental analysis. "
            "Your job is to identify 3-5 key atomic claims and map each one to a verbatim quote from the context. "
            "Do NOT call any external tools. Use ONLY the information provided in your context. "
            "Any claim you cannot map to a verbatim quote should be marked 'Speculative'."
        ),
        llm=critic_llm,
        tools=[],
        allow_delegation=False,
        verbose=True,
    )

    logic_critic = Agent(
        role="Adversarial Logic Critic",
        goal="Rigorously challenge the mathematical and logical soundness of theoretical research claims.",
        backstory=(
            "You are a skeptic. You do not believe results without proof. "
            "In THEORETICAL MODE, you are the final gatekeeper. You must look for logical fallacies, "
            "hidden assumptions, and inconsistencies in the derived results."
        ),
        llm=critic_llm,
        allow_delegation=False,
        verbose=True,
    )

    academic_writer = Agent(
        role="Senior Academic Publisher (JSON Structured Output)",
        goal=f"Draft a formal research paper as structured JSON using ONLY verified observations.",
        backstory=(
            "You are a precision scientific writer. You output ONLY valid JSON. "
            "You integrate findings from the Researcher, Scientist, and Critic into a cohesive narrative. "
            "Your output must adhere to the high-fidelity JSON schema: metadata and sections."
        ),
        llm=reasoning_llm,
        tools=[],
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
        description=(
            f"You have received a structured literature summary from the Principal Researcher about: '{topic}'. "
            f"User constraints: {user_commands if user_commands else 'None'}. "
            "Using ONLY the research context provided, formulate ONE precise, falsifiable hypothesis. "
            "The hypothesis MUST: (1) name specific variables and their relationship, "
            "(2) be measurable via simulation or mathematical proof, "
            "(3) cite novelty by contrasting with known findings from the literature. "
            "Do NOT ask for more information. Do NOT use any tools. Derive the hypothesis from the context."
        ),
        expected_output="A single falsifiable hypothesis statement in the format: 'We hypothesize that [X] will [effect] [Y] under [conditions], because [evidence from literature].'",
        agent=lead_scientist,
        context=[task_research],
        async_execution=False
    )

    # --- Execution Mode Logic ---
    execution_enabled = (llm_config or {}).get("execution_enabled", True)
    
    if execution_enabled:
        experiment_desc = "Write an E2B/Modal sandbox Python script testing the hypothesis. Use RetrieveGroundingSpansTool if you need algorithm details. Execute it. If it fails, read STDERR, do the 'Karpathy Move' and fix it."
        experiment_expected = "The final working Python code, along with stdout metrics proving/disproving the claim."
        experiment_agent = ml_engineer
    else:
        experiment_desc = "THEORETICAL MODE: Perform a deep static analysis of the hypothesis. Derive expected results using mathematical and logical soundness. Use RetrieveGroundingSpansTool for grounding."
        experiment_expected = "A detailed theoretical proof and expected outcome metrics, formatted for inclusion in a results section."
        experiment_agent = ml_engineer

    task_experiment = Task(
        description=experiment_desc,
        expected_output=experiment_expected,
        agent=experiment_agent,
        context=[task_hypothesis],
        async_execution=False
    )

    task_logic_verify = Task(
        description="Review the theoretical derivation or experimental setup. Identify logical gaps or potential simulation artifacts. If in THEORETICAL MODE, provide a formal adversarial critique.",
        expected_output="A list of 3-5 critical logical validations or potential points of failure.",
        agent=logic_critic,
        context=[task_experiment],
        async_execution=False
    )

    task_verify = Task(
        description=(
            "Review the research findings, hypothesis, experiment, and logic critique provided in your context. "
            "Identify 3-5 key atomic claims from this body of work. "
            "For each claim, find a verbatim supporting quote from the context. "
            "Do NOT use any external tools — use ONLY the context already provided. "
            "Output a JSON array of Grounding Card objects with fields: 'claim' and 'verbatim_quote'. "
            "If a claim cannot be verified, set verbatim_quote to 'SPECULATIVE — no direct evidence found.'"
        ),
        expected_output="A JSON array of Grounding Card objects: [{\"claim\": \"...\", \"verbatim_quote\": \"...\"}]",
        agent=verifier,
        context=[task_research, task_hypothesis, task_experiment, task_logic_verify],
        async_execution=False
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
            _progress(6, f"Result extraction failed: {e}", "warning", is_internal=True)
    task_experiment.callback = task_experiment_cb

    # --- Modular Writing Tasks (DEEP SEQUENTIAL) ---
    prompts = PAPER_JSON_STRUCTURE["prompts"]
    
    task_intro = Task(
        description=prompts["introduction"].replace("{{topic}}", topic),
        expected_output="A JSON object for the Introduction section.",
        agent=academic_writer,
        context=[task_research, task_hypothesis],
        async_execution=False
    )

    task_rw = Task(
        description=prompts["related_work"],
        expected_output="A JSON object for the Related Work section.",
        agent=academic_writer,
        context=[task_research],
        async_execution=False
    )

    task_methodology = Task(
        description=prompts["methodology"],
        expected_output="A JSON object for the Methodology section.",
        agent=academic_writer,
        context=[task_hypothesis, task_experiment],
        async_execution=False
    )

    task_results = Task(
        description=prompts["results"],
        expected_output="A JSON object for the Results section.",
        agent=academic_writer,
        context=[task_experiment, task_verify],
        async_execution=False
    )

    task_conclusion = Task(
        description=prompts["conclusion"],
        expected_output="A JSON object for the Conclusion section.",
        agent=academic_writer,
        context=[task_intro, task_methodology, task_results],
        async_execution=False
    )

    task_abstract = Task(
        description=prompts["abstract"],
        expected_output="A JSON object for the Abstract section.",
        agent=academic_writer,
        context=[task_intro, task_methodology, task_results],
        async_execution=False
    )

    # FINAL ASSEMBLY TASK
    task_compilation = Task(
        description=prompts["assembly"],
        expected_output="A single complete valid JSON object containing metadata and all sections.",
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
            _progress(2, f"RAG extraction failed: {e}", "warning", is_internal=True)
            print(f"[RAG] Failed to extract indexed chunks: {e}")
            
        _progress(2, "Extraction Engine Completed (Grounding Spans Mined)", "done", output=task_output.raw)
    task_research.callback = task_research_cb

    def task_hypothesis_cb(task_output): _progress(4, "Reasoning Core: Hypothesis Proposed", "done", output=task_output.raw)
    task_hypothesis.callback = task_hypothesis_cb

    # Corrected callback for experiment to use our internal logic
    # (already handled in methodology task setup above via nonlocal result_card)
    def task_experiment_res_cb(task_output):
        # We need to call the existing nonlocal logic AND update progress
        task_experiment_cb(task_output)
        _progress(6, "Sandbox Execution complete", "done", output=task_output.raw)
    task_experiment.callback = task_experiment_res_cb

    def task_logic_verify_cb(task_output):
        _progress(7, "Logic Critic: Adversarial Review Complete", "done", output=task_output.raw)

    task_logic_verify.callback = task_logic_verify_cb

    def task_verify_cb(task_output):
        # Validate hallucination threshold (verbatim_quote + SPECULATIVE prefix per task prompt)
        try:
            val = task_output.raw or ""
            start, end = val.find("["), val.rfind("]")
            if start == -1 or end == -1:
                raise json.JSONDecodeError("no array", val, 0)
            parsed = json.loads(val[start : end + 1])
            if not isinstance(parsed, list):
                parsed = parsed.get("claims", []) if isinstance(parsed, dict) else []
            claims = [c for c in parsed if isinstance(c, dict)]
            if not claims:
                _progress(
                    8,
                    "Adversarial Critic: no claims parsed.",
                    "warning",
                    output=task_output.raw,
                    is_internal=True,
                )
                return
            speculative = sum(
                1
                for c in claims
                if str(c.get("verbatim_quote", "")).strip().upper().startswith("SPECULATIVE")
            )
            if speculative > len(claims) / 2:
                _progress(
                    8,
                    f"Adversarial Critic: high speculative ratio ({speculative}/{len(claims)}). Halt.",
                    "error",
                )
                raise ValueError(
                    "Adversarial Verifier Halt: hallucination ratio > 50%. Reflexion required."
                )
            _progress(8, "Adversarial Critic: RefLens Verification Passed", "done", output=task_output.raw)
        except json.JSONDecodeError:
            _progress(
                8,
                "Adversarial Critic: JSON parse error during verification.",
                "warning",
                output=task_output.raw,
                is_internal=True,
            )

    task_verify.callback = task_verify_cb

    # Writing callbacks — one unique step number per task for resume-safe get_completed_tasks()
    def task_intro_cb(o):
        _progress(9, "Writing: Introduction Drafted", "done", output=o.raw)

    task_intro.callback = task_intro_cb

    def task_rw_cb(o):
        _progress(10, "Writing: Related Work Drafted", "done", output=o.raw)

    task_rw.callback = task_rw_cb

    def task_methodology_cb(o):
        _progress(11, "Writing: Methodology Drafted", "done", output=o.raw)

    task_methodology.callback = task_methodology_cb

    def task_results_cb(o):
        _progress(12, "Writing: Results Drafted", "done", output=o.raw)

    task_results.callback = task_results_cb

    def task_conclusion_cb(o):
        _progress(13, "Writing: Conclusion Drafted", "done", output=o.raw)

    task_conclusion.callback = task_conclusion_cb

    def task_abstract_cb(o):
        _progress(14, "Writing: Abstract Drafted", "done", output=o.raw)

    task_abstract.callback = task_abstract_cb

    def task_compilation_cb(o):
        _progress(15, "Final Manuscript Compiled & Synchronized", "done", output=o.raw)

    task_compilation.callback = task_compilation_cb

    # ==========================================
    # RESUMPTION LOGIC
    # ==========================================
    all_tasks_ordered = [
        (2, task_research),
        (4, task_hypothesis),
        (6, task_experiment),
        (7, task_logic_verify),
        (8, task_verify),
        (9, task_intro),
        (10, task_rw),
        (11, task_methodology),
        (12, task_results),
        (13, task_conclusion),
        (14, task_abstract),
        (15, task_compilation),
    ]

    tasks_to_run = []
    for step_idx, task_obj in all_tasks_ordered:
        if step_idx in completed_tasks:
            print(f"[CrewAI] Skipping Step {step_idx}: Task already completed.")
            # Inject cached output so downstream tasks can use it
            task_obj.output = TaskOutput(
                description=task_obj.description,
                raw=completed_tasks[step_idx],
                agent=task_obj.agent.role if task_obj.agent else "System",
            )
        else:
            tasks_to_run.append(task_obj)

    # ==========================================
    # CREW
    # ==========================================
    
    _progress(1, "Orchestrating agents via Real-Time Router...")
    crew = Crew(
        agents=[researcher, lead_scientist, ml_engineer, logic_critic, verifier, academic_writer],
        tasks=tasks_to_run,
        process=Process.sequential,
        verbose=True,
        tracing=True
    )

    print("[CrewAI] Kicking off Deep LaTeX Lifecycle...")
    try:
        final_body = crew.kickoff()
    except Exception as e:
        print(f"[CrewAI] Reflexion Error: {e}")
        raise

    # Final Manuscript Extraction (JSON) — multi-strategy robust parser
    paper_json = {}
    try:
        raw_output = str(final_body)
        # Strip markdown code fences if present
        cleaned = raw_output.strip()
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            cleaned = '\n'.join(lines[1:] if lines[0].startswith('```') else lines)
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3].strip()
        # Strategy 1: find outermost { ... }
        json_start = cleaned.find('{')
        json_end = cleaned.rfind('}')
        if json_start != -1 and json_end != -1:
            json_str = cleaned[json_start:json_end+1]
            paper_json = json.loads(json_str)
        else:
            paper_json = json.loads(cleaned)
        # Validate structure
        if not paper_json.get('metadata') or not isinstance(paper_json.get('sections'), list):
            raise ValueError("Invalid paper structure")
    except Exception as e:
        print(f"[CrewAI] Warning: Failed to parse final paper JSON: {e}")
        # Fallback structure
        paper_json = {
            "metadata": {"title": topic.title(), "author": "ARS Assistant", "date": "May 2026", "institution": "GLA Lab"},
            "sections": [
                {"id": "raw", "type": "content", "title": "Manuscript", "content": str(final_body)}
            ]
        }

    # Summary formatting (RefLens Grounding extraction) — always store parsed array
    summary_data = {}
    try:
        if task_verify.output and task_verify.output.raw:
            raw_vid = task_verify.output.raw
            # Try finding JSON array
            arr_start = raw_vid.find('[')
            arr_end = raw_vid.rfind(']')
            if arr_start != -1 and arr_end != -1:
                json_block = raw_vid[arr_start:arr_end+1]
                parsed_cards = json.loads(json_block)
                summary_data = {"grounding": parsed_cards}  # Always store as parsed list
            else:
                summary_data = {"grounding": []}
    except Exception:
        summary_data = {"grounding": []}

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
                        "text": card.get("evidence_span")
                        or card.get("verbatim_quote", ""),
                        "source": card.get("claim", ""),
                        "url": "",
                    }
                    for card in grounding_cards
                    if isinstance(card, dict)
                    and (card.get("evidence_span") or card.get("verbatim_quote"))
                ]
                if grounding_spans:
                    index_grounding_spans(run_id, topic, grounding_spans)
                    print(f"[CrewAI] Indexed {len(grounding_spans)} grounding spans into ChromaDB")
    except Exception as e:
        print(f"[CrewAI] Warning: Failed to index grounding spans: {e}")

    # Cleanup DB: Free vector storage after run is done to avoid bloating Chroma
    # clear_run_spans(run_id)

    return {
        "paper_json": paper_json,
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
            "You are a meticulous editor. You take an existing manuscript JSON and refine it "
            "to address specific critiques while maintaining structured JSON integrity."
        ),
        llm=reasoning_llm,
        allow_delegation=False,
        verbose=True,
    )

    task_refine = Task(
        description=(
            f"Original Paper Topic: {topic}\n"
            f"Feedback: {feedback}\n\n"
            f"Original JSON Content:\n{json.dumps(run_data.get('paper_json', {}))}\n\n"
            "Please rewrite the parts of the paper relevant to the feedback. "
            "Ensure the final output is a complete, well-structured valid JSON object with the same schema."
        ),
        expected_output="The complete refined research paper in structured JSON.",
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
