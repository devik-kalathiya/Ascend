"""Day gating: the next day stays locked until the previous day passes its review."""
from typing import Any, Dict, List, Optional

from .state import load_state


def is_day_passed(state: Optional[Dict[str, Any]], day: Dict[str, Any]) -> bool:
    reviews = (state or {}).get("reviews") or {}
    return bool((reviews.get(str(day["day"])) or {}).get("passed"))


def check_day_gate(project_path, days: List[Dict[str, Any]], current_step: int) -> Dict[str, Any]:
    """The next step is locked when it opens a new day and the previous day has not passed its review.
    Returns {locked, day?, previous?}."""
    state = load_state(project_path)
    next_step = current_step + 1
    day = next((d for d in days if next_step in d["steps"]), None)
    if day is None or day["index"] == 0:
        return {"locked": False, "day": day}

    previous = days[day["index"] - 1]
    if is_day_passed(state, previous):
        return {"locked": False, "day": day}
    return {"locked": True, "day": day, "previous": previous}


def default_review_day(days: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
    """Which day `jibun review` should look at when none is given."""
    done = state.get("currentStep") or 0
    for d in days:
        if not is_day_passed(state, d) and (any(n <= done for n in d["steps"]) or d["index"] == 0):
            return d
    return days[-1]
