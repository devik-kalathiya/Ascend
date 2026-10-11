import os
from pathlib import Path

from .. import logger
from ..state import load_state
from ..validator import parse_days


def status(cwd=None) -> None:
    logger.header("Jibun — Status")
    cwd = Path(cwd or os.getcwd())
    state = load_state(cwd)
    instruction_path = cwd / "INSTRUCTION.md"

    if not state or not instruction_path.exists():
        logger.error("No Jibun project here. Run `jibun init` first.")
        return

    days = parse_days(instruction_path)
    logger.info(f"Steps completed: {state.get('currentStep')}/{state.get('totalSteps')}")
    print("")

    for d in days:
        done = sum(1 for n in d["steps"] if n <= state["currentStep"])
        r = state["reviews"].get(str(d["day"]))
        if r:
            label = f"review passed ({r.get('score')}/100)" if r.get("passed") else f"review: not passed ({r.get('score')}/100)"
        else:
            label = "not reviewed"
        mark = "✔" if (r and r.get("passed")) else "◐" if done == len(d["steps"]) else " "
        print(f" {mark} Day {d['day']}: {d['title']} — {done}/{len(d['steps'])} steps — {label}")
    print("")
