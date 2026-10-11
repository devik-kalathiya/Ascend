"""Hints that look at the learner's own code, with an offline fallback."""
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

from . import logger as default_logger
from .docs_resolver import extract_concepts, resolve_docs
from .planner import get_hint_from_groq
from .util import read_text
from .validator import validate_step

PATH_IN_BACKTICKS = re.compile(r"`((?:[\w@.\-]+/)*[\w@.\-]+\.(?:html|css|js|mjs|json|md))`")
MAX_FILES = 3
MAX_CHARS = 3000


def build_hint_context(step_content: str, project_path) -> str:
    """The learner's own code for the files this step talks about, plus what is still failing."""
    parts: List[str] = []

    validation = validate_step(step_content, project_path)
    if not validation["passed"]:
        parts.append(f"Validation currently failing: {validation['reason']}")

    files = list(dict.fromkeys(PATH_IN_BACKTICKS.findall(step_content)))[:MAX_FILES]
    for rel in files:
        abs_path = Path(project_path) / rel
        if not abs_path.exists():
            parts.append(f"File {rel}: does not exist yet.")
            continue
        text = read_text(abs_path)
        body = text[:MAX_CHARS] + "\n…(truncated)" if len(text) > MAX_CHARS else (text or "(empty)")
        parts.append(f"File {rel}:\n{body}")

    return "\n\n".join(parts)


def _head_ok(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=4):
            return True
    except urllib.error.HTTPError as e:
        return e.code not in (404, 410)
    except Exception:
        return True  # network errors keep the link


def verify_docs(urls: List[str]) -> List[str]:
    """Drop doc links that clearly do not exist (models sometimes invent URLs)."""
    if not urls:
        return []
    with ThreadPoolExecutor(max_workers=len(urls)) as pool:
        ok = list(pool.map(_head_ok, urls))
    return [u for u, good in zip(urls, ok) if good]


def offline_hint(step_content: str, project_path) -> Dict[str, Any]:
    validation = validate_step(step_content, project_path)
    concepts = extract_concepts(step_content)
    docs = list(dict.fromkeys(url for c in concepts for url in resolve_docs(c)))[:2]

    if validation["passed"]:
        hint = 'This step looks complete. Re-read the "Why?" section and check you understand the idea behind it.'
    else:
        hint = (f"The AI mentor is offline, so here is what the checker sees. {validation['reason']}. "
                'Re-read the "How?" section and compare it with your files.')

    return {
        "hint": hint,
        "docs": docs,
        "question": "What does this step contribute to the final app, and what would break without it?",
        "source": "offline",
    }


def get_hint(step_content: str, project_path, verify: bool = True) -> Dict[str, Any]:
    """Hint with the learner's code attached; falls back to local docs when the API is unreachable."""
    try:
        context = build_hint_context(step_content, project_path)
        hint = get_hint_from_groq(step_content, context)
        docs = verify_docs(hint["docs"]) if verify else hint["docs"]
        return {**hint, "docs": docs, "source": "ai"}
    except Exception:
        return offline_hint(step_content, project_path)


def print_hint(log, h: Dict[str, Any]) -> None:
    log.divider()
    print("")
    print(h["hint"])
    print("")
    if h.get("docs"):
        log.info("Relevant docs:")
        for d in h["docs"]:
            print(f"   {d}")
    if h.get("question"):
        log.divider()
        log.hint("Think about this:")
        print(f"   {h['question']}")
    if h.get("source") == "offline":
        log.warn("Offline mode: set GROQ_API_KEY / check your connection for full AI hints.")
    log.divider()
