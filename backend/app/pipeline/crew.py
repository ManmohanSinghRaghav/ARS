"""
CrewAI Orchestration pipeline.
Replaces LangChain/LangGraph completely.
"""
import os
import json
from crewai import Agent, Task, Crew, Process
from app.pipeline.tools import search_literature, sandbox_execute
from app.pipeline.llm_factory import get_llm
from app.pipeline.progress import add_step

def run_crew_pipeline(topic: str, run_id: str, llm_config: dict | None = None) -> dict:
    """
    Builds the CrewAI agents and tasks, then kicks off the pipeline.
    Returns a dictionary of artifacts (generated code, reasoning, paper).
    """

    # Fetch the LangChain-compatible wrapped LLM
    llm = get_llm(llm_config)

    # Helper function to report to UI
    def _progress(step: int, title: str, status: str = "running"):
        add_step(run_id, step, 10, title, status)
        print(f"[CrewAI] Step {step}/10 - {title}")

    # ==========================================
    # AGENTS
    # ==========================================
    researcher = Agent(
        role="Principal Literature Researcher",
        goal=f"Thoroughly analyze and extract state-of-the-art information about: {topic}",
        backstory=(
            "You are an expert AI literature reviewer. "
            "Your job is to read papers across the academic web, identify key findings, methodologies, "
            "and explicitly point out gaps in the scientific literature regarding the given topic."
        ),
        llm=llm,
        tools=[search_literature],
        allow_delegation=False,
        verbose=True,
    )

    lead_scientist = Agent(
        role="Lead Research Scientist",
        goal="Synthesize literature into a radically novel, testable, and ground-breaking hypothesis.",
        backstory=(
            "You are a visionary Lead Scientist. You never propose ideas that have already been perfectly solved. "
            "You look at the literature gaps provided by the Researcher and construct a hypothesis that pushes the boundary. "
            "Your hypotheses must be mathematically or computationally testable using standard Python ML libraries."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

    ml_engineer = Agent(
        role="Machine Learning Simulation Engineer",
        goal="Autonomously write, deploy, test, and fix python simulations to validate the proposed hypothesis.",
        backstory=(
            "You are a Senior ML Engineer. Given a hypothesis, you write clean, self-contained Python scripts. "
            "You MUST use your SandboxTool to execute the code. "
            "If the SandboxTool returns an error, you must analyze the stack trace, rewrite the code, and test it again! "
            "You only finish your task when the code successfully proves or tests the hypothesis."
        ),
        llm=llm,
        tools=[sandbox_execute],
        allow_delegation=False,
        verbose=True,
    )

    academic_writer = Agent(
        role="Senior Academic Publisher",
        goal="Draft a highly formal, mathematically rigorous, and structurally perfect research paper.",
        backstory=(
            "You are a widely cited Academic Author. You compile raw findings into beautiful Markdown papers. "
            "You must include an Abstract, Introduction, Methodology, Experimental Results (referencing the raw outputs directly), "
            "Discussion, and a clear Conclusion."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

    # ==========================================
    # TASKS
    # ==========================================
    
    task_research = Task(
        description=f"Thoroughly search ArXiv and Web resources for the topic: '{topic}'. Identify exactly where the current boundary of knowledge sits and list 3 major gaps.",
        expected_output="A structured summary containing core domain concepts, key known findings, methodological standards, and a list of identified gaps.",
        agent=researcher,
    )
    
    task_hypothesis = Task(
        description="Review the researcher's extracted literature gaps and create a SINGLE, testable, novel scientific hypothesis.",
        expected_output="A detailed 1-2 paragraph description of the proposed hypothesis, explaining WHY it is novel and explicitly HOW simulated experiments will test it.",
        agent=lead_scientist,
    )

    task_experiment = Task(
        description="Write a complete Python script testing the Lead Scientist's hypothesis using Numpy/PyTorch. Execute the code using the SandboxTool. If it fails, read the compiler errors and rewrite it, running the SandboxTool until success is achieved.",
        expected_output="The final working raw Python code, along with a detailed overview of the mathematical results outputted from the Sandbox STDOUT.",
        agent=ml_engineer,
    )

    task_writing = Task(
        description=f"Read the final experimental results and the initial hypothesis. Draft a comprehensive markdown Research Paper for the topic: {topic}. Include the python code blocks inline, explain the data, and conclude whether the hypothesis stood strong.",
        expected_output="A complete, professional markdown string representing the final generated Paper.",
        agent=academic_writer,
    )

    def task_research_cb(*args): _progress(2, "Literature Review Completed", "done")
    task_research.callback = task_research_cb

    def task_hypothesis_cb(*args): _progress(4, "Hypothesis Proposed", "done")
    task_hypothesis.callback = task_hypothesis_cb

    def task_experiment_cb(*args): _progress(7, "Experiments Code Executed", "done")
    task_experiment.callback = task_experiment_cb

    def task_writing_cb(*args): _progress(9, "Research Paper Drafted", "done")
    task_writing.callback = task_writing_cb

    # ==========================================
    # CREW
    # ==========================================
    
    _progress(1, "Orchestrating agents...")
    crew = Crew(
        agents=[researcher, lead_scientist, ml_engineer, academic_writer],
        tasks=[task_research, task_hypothesis, task_experiment, task_writing],
        process=Process.sequential,
        verbose=True
    )

    print("[CrewAI] Kicking off process...")
    try:
        final_paper = crew.kickoff()
    except Exception as e:
        print(f"[CrewAI] Critical Pipeline Crash: {e}")
        raise e

    # Extract outputs from the tasks
    # CrewAI Tasks store `.output.raw` once completed
    return {
        "final_paper": str(final_paper),
        "hypothesis": str(task_hypothesis.output.raw_content if task_hypothesis.output else "N/A"),
        "execution_output": str(task_experiment.output.raw_content if task_experiment.output else "N/A"),
        "retrieved_docs": str(task_research.output.raw_content if task_research.output else "N/A"),
        # CrewAI doesn't natively split the python code block easily unless using Pydantic Outputs.
        # We'll just pass everything as one massive overview and parse code in UI if requested, 
        # or we just rely on execution_output containing the logs.
    }
