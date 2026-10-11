"""Curriculum and hint generation prompts."""
import re
from typing import Any, Dict

from .llm import chat, extract_json
from .prompts import HINT_SYSTEM_PROMPT, PLANNER_SYSTEM_PROMPT


def clean_curriculum(raw: str) -> str:
    """Remove ``` fences some models wrap around the whole markdown file."""
    out = re.sub(r"^\s*```(?:markdown|md)?\s*\n", "", raw, flags=re.I)
    out = re.sub(r"\n```\s*$", "", out, flags=re.I)
    return out.strip() + "\n"


def generate_instructions(idea_content: str) -> str:
    raw = chat(system=PLANNER_SYSTEM_PROMPT, user=idea_content, temperature=0.7, max_tokens=6000)
    return clean_curriculum(raw)


def get_hint_from_groq(step_content: str, context: str = "") -> Dict[str, Any]:
    """`context` is the learner's current code + failing checks (makes the hint specific)."""
    if context:
        user = (f"{step_content}\n\n---\nLEARNER'S CURRENT STATE "
                f"(use it to make the hint specific, never paste a solution):\n{context}")
    else:
        user = step_content

    raw = chat(system=HINT_SYSTEM_PROMPT, user=user, temperature=0.8, max_tokens=1024, json_mode=True)

    try:
        parsed = extract_json(raw)
        return {
            "hint": parsed.get("hint") or "Keep going — you are closer than you think.",
            "docs": parsed["docs"] if isinstance(parsed.get("docs"), list) else [],
            "question": parsed.get("question") or "What is the purpose of this step in the overall architecture?",
        }
    except Exception:
        return {"hint": raw, "docs": [], "question": "What part of this step feels unclear to you?"}
