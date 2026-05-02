from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.auth.dependencies import User, get_current_user
from app.pipeline.llm_factory import get_tier_llm
from app.database import get_db

router = APIRouter(prefix="/api/discovery", tags=["Discovery"])


class ChatMessage(BaseModel):
    role: str
    content: str


class DiscoveryChatRequest(BaseModel):
    messages: List[ChatMessage]
    vibe: Optional[str] = "Deep Academic"


class TopicSuggestRequest(BaseModel):
    seed: str
    vibe: Optional[str] = "Deep Academic"


DISCOVERY_SYSTEM_PROMPT = """
You are the ARS Topic Discovery Assistant — an elite research strategist powered by advanced reasoning.
Your goal is to transform a vague research seed into multiple high-novelty, specific, and publishable research topics.

Rules:
1. Generate EXACTLY 4 distinct research topic suggestions.
2. Each must be specific enough to be validated via simulation, math proof, or literature analysis.
3. Avoid generic topics — introduce novel angles, cross-domain intersections, or adversarial twists.
4. Output MUST be valid JSON. No markdown, no prose outside the JSON.

Output format:
{
  "suggestions": [
    {
      "title": "Full research paper title",
      "angle": "One sentence describing the novel angle or contribution",
      "vibe": "Deep Academic" | "Rapid Synthesis" | "Adversarial Audit"
    }
  ]
}
"""

DISCOVERY_CHAT_PROMPT = """
You are the ARS Topic Discovery Assistant. Your goal is to help the user refine a vague research idea into a high-novelty, specific, and testable scientific topic.

Strategies:
1. If the idea is broad, suggest specific sub-domains.
2. If the idea is common, suggest a novel 'twist' or intersection (e.g., AI + Quantum).
3. Ensure the topic can be validated via simulation or literature analysis.

Always end by suggesting 2-3 refined 'Novel Titles'.
If the user is satisfied, provide a FINAL_BLUEPRINT in JSON format containing:
{
  "title": "...",
  "hypothesis": "...",
  "suggested_vibe": "Deep Academic" | "Rapid Synthesis" | "Adversarial Audit"
}
"""


@router.post("/suggest")
async def suggest_topics(
    payload: TopicSuggestRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Use the heavy reasoning LLM to generate 4 novel, specific research topic suggestions
    from a seed topic. Used by the 'Optimize Topic' button on the dashboard.
    """
    llm = get_tier_llm("reasoning")  # Heavy LLM for quality suggestions

    # Pull the user's LLM config from Firestore (best-effort, for API key)
    try:
        from app.security.crypto import decrypt_str
        from app.config import get_settings
        defaults = get_settings()
        doc = db.collection("user_settings").document(current_user.id).get()
        us = doc.to_dict() if doc.exists else {}

        def _dec(field):
            try:
                return decrypt_str(us.get(field))
            except Exception:
                return ""

        user_llm_config = {
            "gemini_api_key": (_dec("gemini_api_key") if us.get("gemini_api_key") else "") or defaults.GEMINI_API_KEY,
            "heavy_model": us.get("heavy_model") or defaults.DEFAULT_HEAVY_MODEL,
            "heavy_rpm": us.get("heavy_rpm") or defaults.DEFAULT_HEAVY_RPM,
            "heavy_tpm": us.get("heavy_tpm") or defaults.DEFAULT_HEAVY_TPM,
        }
        llm = get_tier_llm("reasoning", user_llm_config)
    except Exception:
        pass  # Fall back to default LLM

    prompt = (
        f"{DISCOVERY_SYSTEM_PROMPT}\n\n"
        f"Research Seed: \"{payload.seed}\"\n"
        f"Target Vibe: {payload.vibe}\n\n"
        "Generate 4 novel research topic suggestions. Output ONLY valid JSON."
    )

    try:
        raw = llm.call(prompt)
        # Strip markdown code fences if any
        import re, json
        cleaned = re.sub(r"^```(?:json)?\s*|```\s*$", "", raw.strip(), flags=re.MULTILINE).strip()
        # Find the JSON object
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if not json_match:
            raise ValueError("No JSON found in LLM response")
        parsed = json.loads(json_match.group())
        return parsed
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Topic suggestion failed: {e}")


@router.post("/chat")
async def discovery_chat(
    payload: DiscoveryChatRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Refine a vague research topic through conversation."""
    llm = get_tier_llm("extraction")  # Light engine for speed

    # Pull the user's LLM config from Firestore (same pattern as suggest_topics)
    try:
        from app.security.crypto import decrypt_str
        from app.config import get_settings

        defaults = get_settings()
        doc = db.collection("user_settings").document(current_user.id).get()
        us = doc.to_dict() if doc.exists else {}

        def _dec(field):
            try:
                return decrypt_str(us.get(field))
            except Exception:
                return ""

        user_llm_config = {
            "gemini_api_key": (_dec("gemini_api_key") if us.get("gemini_api_key") else "")
            or defaults.GEMINI_API_KEY,
            "groq_api_key": (_dec("groq_api_key") if us.get("groq_api_key") else "")
            or defaults.GROQ_API_KEY,
            "openai_api_key": (_dec("openai_api_key") if us.get("openai_api_key") else "")
            or defaults.OPENAI_API_KEY,
            "claude_api_key": (_dec("claude_api_key") if us.get("claude_api_key") else "")
            or defaults.CLAUDE_API_KEY,
            "light_model": us.get("light_model") or defaults.DEFAULT_LIGHT_MODEL,
            "light_rpm": us.get("light_rpm") or defaults.DEFAULT_LIGHT_RPM,
            "light_tpm": us.get("light_tpm") or defaults.DEFAULT_LIGHT_TPM,
        }
        llm = get_tier_llm("extraction", user_llm_config)
    except Exception:
        pass  # Fall back to default LLM

    history = "\n".join([f"{m.role.upper()}: {m.content}" for m in payload.messages])
    full_prompt = f"{DISCOVERY_CHAT_PROMPT}\n\nUser Vibe: {payload.vibe}\n\nHistory:\n{history}\n\nASSISTANT:"

    try:
        response = llm.call(full_prompt)
        return {"content": response.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery chat failed: {e}")
