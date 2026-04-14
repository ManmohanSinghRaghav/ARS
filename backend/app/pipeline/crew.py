"""
CrewAI Orchestration pipeline.
Replaces LangChain/LangGraph completely.
"""
import os
import json
from crewai import Agent, Task, Crew, Process
from app.pipeline.tools import search_literature, sandbox_execute
from app.pipeline.llm_factory import get_tier_llm
from app.pipeline.progress import add_step

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
    router_llm = get_tier_llm("router", llm_config)

    # Helper function to report to UI
    def _progress(step: int, title: str, status: str = "running", detail: str = ""):
        add_step(run_id, step, 10, title, status, detail)
        print(f"[CrewAI] Step {step}/10 - {title}")

    # ==========================================
    # AGENTS (v3.1 Architecture)
    # ==========================================
    researcher = Agent(
        role="Principal Literature Researcher",
        goal=f"Mines structured Grounding Spans and latest papers about: {topic}",
        backstory=(
            "You are an expert AI literature parsing engine. "
            "You use the extraction engine for high-volume parsing. "
            "Extract verbatim 'Grounding Spans' from ArXiv and web content. "
            "Identify missing knowledge edges."
        ),
        llm=extraction_llm,
        tools=[search_literature],
        allow_delegation=False,
        verbose=True,
    )

    lead_scientist = Agent(
        role="Lead Research Scientist",
        goal="Synthesize structured observations into a novel, falsifiable scientific hypothesis.",
        backstory=(
            f"You are a visionary intent architect operating in a '{target_vibe}' vibe. "
            "You leverage System 2 thinking to formulate breakthrough testable claims. "
            "Hypotheses must explicitly define variable relationships measurable via code."
        ),
        llm=reasoning_llm,
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
        ),
        llm=reasoning_llm,
        tools=[sandbox_execute],
        allow_delegation=False,
        verbose=True,
    )

    verifier = Agent(
        role="Adversarial RefLens Critic",
        goal="Check hallucinated citations and logically dissect experimental claims.",
        backstory=(
            "You act as the 'Verifier'. You decompose synthesis into 'Atomic Claims' and perform Multi-Hop Tracing. "
            "Any claim lacking strict verbatim evidence is marked 'Speculative'."
        ),
        llm=critic_llm,
        allow_delegation=False,
        verbose=True,
    )

    academic_writer = Agent(
        role="Senior Academic Publisher",
        goal=f"Draft a formal, publication-ready research paper with the requested '{target_vibe}' tone.",
        backstory=(
            "You weave verified claims and experimental results into beautiful, rigorous Markdown papers with LaTeX formulas. "
            "Outputs must follow the Cognitive Surface format including Grounding Spans."
        ),
        llm=reasoning_llm,
        allow_delegation=False,
        verbose=True,
    )

    # ==========================================
    # TASKS
    # ==========================================
    
    task_research = Task(
        description=f"Parse the research topic: '{topic}'. Keep these sub-commands in mind: {user_commands}. Use tools to mine ArXiv/Web. Extract verbatim 'Grounding Spans' and metadata.",
        expected_output="A structured output mapping 3 major gaps and verbatim grounding spans extracted from literature.",
        agent=researcher,
    )
    
    task_hypothesis = Task(
        description=f"Review the researcher's extracted spans and any user constraints: {user_commands}. Formulate a SINGLE falsifiable hypothesis using System 2 reasoning.",
        expected_output="A mathematically or computationally testable hypothesis statement, justifying novelty.",
        agent=lead_scientist,
    )

    task_experiment = Task(
        description="Write an E2B/Modal sandbox Python script testing the hypothesis. Execute it. If it fails, read STDERR, do the 'Karpathy Move' and fix it.",
        expected_output="The final working Python code, along with stdout metrics proving/disproving the claim.",
        agent=ml_engineer,
    )

    task_verify = Task(
        description="Verify the experiment outputs and hypothesis claims against the researcher's grounding spans. Output MUST be a STRICT JSON array of objects with keys: {'claim': string, 'evidence_span': string, 'status': 'Verified' | 'Speculative'}.",
        expected_output="A JSON array of formal 'Grounding Card' objects mapping each atomic claim to verbatim quotes. If confidence < 90%, mark 'Speculative'.",
        agent=verifier,
    )

    task_writing = Task(
        description=f"Compile all verified claims, code, and findings into a strict '{target_vibe}' Markdown Research Paper. Include LaTeX formulas (e.g., $E=mc^2$). DO NOT include 'Speculative' claims.",
        expected_output="A complete, professional markdown string representing the final generated Paper.",
        agent=academic_writer,
    )

    def task_research_cb(*args): _progress(2, "Extraction Engine Completed (Grounding Spans Mined)", "done")
    task_research.callback = task_research_cb

    def task_hypothesis_cb(*args): _progress(4, "Reasoning Core: Hypothesis Proposed", "done")
    task_hypothesis.callback = task_hypothesis_cb

    def task_experiment_cb(*args): _progress(6, "Sandbox Execution: Karpathy Move complete", "done")
    task_experiment.callback = task_experiment_cb

    def task_verify_cb(*args):
        # Validate hallucination threshold
        try:
            val = task_verify.output.raw_content
            parsed = json.loads(val[val.find('['):val.rfind(']')+1])
            speculative_ops = sum(1 for c in parsed if c.get('status') == 'Speculative')
            if speculative_ops > len(parsed) / 2:
                 _progress(8, f"Adversarial Critic: Tracing failed. High Speculative claims ({speculative_ops}). Halt triggered.", "error")
                 raise ValueError("Adversarial Verifier Halt: Hallucination ratio exceeded > 50%. Reflexion required.")
            _progress(8, "Adversarial Critic: RefLens Verification Passed", "done")
        except json.JSONDecodeError:
            _progress(8, "Adversarial Critic: JSON parse error during verification.", "done")
            
    task_verify.callback = task_verify_cb

    def task_writing_cb(*args): _progress(10, "Cognitive Surface Generated", "done")
    task_writing.callback = task_writing_cb

    # ==========================================
    # CREW
    # ==========================================
    
    _progress(1, "Orchestrating agents via Real-Time Router...")
    crew = Crew(
        agents=[researcher, lead_scientist, ml_engineer, verifier, academic_writer],
        tasks=[task_research, task_hypothesis, task_experiment, task_verify, task_writing],
        process=Process.sequential,
        verbose=True
    )

    print("[CrewAI] Kicking off Agentic Lifecycle (OODA Loop)...")
    try:
        final_paper = crew.kickoff()
    except Exception as e:
        print(f"[CrewAI] Reflexion Error: {e}")
        raise e

    # Summary formatting (RefLens Grounding extraction)
    summary_data = {}
    try:
        if task_verify.output and task_verify.output.raw_content:
            raw_vid = task_verify.output.raw_content
            json_block = raw_vid[raw_vid.find('['):raw_vid.rfind(']')+1]
            if json_block:
                summary_data = {"grounding": json.loads(json_block)}
            else:
                 summary_data = {"grounding": json.loads(raw_vid)}
    except:
        summary_data = {"grounding": task_verify.output.raw_content if task_verify.output else "FAILED JSON PARSE"}

    return {
        "final_paper": str(final_paper),
        "hypothesis": str(task_hypothesis.output.raw_content if task_hypothesis.output else "N/A"),
        "execution_output": str(task_experiment.output.raw_content if task_experiment.output else "N/A"),
        "retrieved_docs": str(task_research.output.raw_content if task_research.output else "N/A"),
        "summary_data": summary_data
    }
