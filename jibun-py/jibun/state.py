"""Progress stored in <project>/.jibun/state.json (same format as the Node version)."""
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .util import iso_now


def state_path_of(project_path) -> Path:
    return Path(project_path) / ".jibun" / "state.json"


def load_state(project_path) -> Optional[Dict[str, Any]]:
    p = state_path_of(project_path)
    if not p.exists():
        return None
    state = json.loads(p.read_text(encoding="utf-8"))
    state["reviews"] = state.get("reviews") or {}
    return state


def save_state(project_path, patch: Dict[str, Any]) -> Dict[str, Any]:
    """Merge `patch` into state.json, re-reading the file first so that `jibun start`
    and `jibun review` (two terminals) never overwrite each other's changes.
    Review keys are day numbers; JSON stores them as strings, so they are normalised."""
    current = load_state(project_path) or {}
    nxt = {**current, **patch, "lastUpdated": iso_now()}
    if patch.get("reviews"):
        merged = {str(k): v for k, v in (current.get("reviews") or {}).items()}
        merged.update({str(k): v for k, v in patch["reviews"].items()})
        nxt["reviews"] = merged
    p = state_path_of(project_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(nxt, indent=2), encoding="utf-8")
    return nxt
