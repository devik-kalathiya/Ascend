import os
import shutil
from pathlib import Path

from .. import logger
from ..planner import generate_instructions
from ..snapshot import take_snapshot
from ..state import load_state, save_state
from ..util import iso_now, read_text
from ..validator import parse_all_steps, parse_days


def init(force: bool = False, cwd=None) -> None:
    logger.header("Jibun — Init")

    cwd = Path(cwd or os.getcwd())
    idea_path = cwd / "IDEA.md"
    instruction_path = cwd / "INSTRUCTION.md"

    if not idea_path.exists():
        logger.error("IDEA.md not found in this directory.")
        logger.info("Create an IDEA.md file describing your project idea.")
        logger.hint('Try: echo "# My Project\\n\\nI want to build a todo app." > IDEA.md')
        return

    existing = load_state(cwd)
    if existing and (existing.get("currentStep") or 0) > 0 and not force:
        logger.warn(f"You are already on Step {existing['currentStep'] + 1}. Re-running init would erase your progress.")
        logger.hint("Use `jibun init --force` if you really want a new curriculum.")
        return

    logger.success("Found IDEA.md")
    idea_content = read_text(idea_path)
    if not idea_content.strip():
        logger.error("IDEA.md is empty. Write something in it first.")
        return

    logger.info("Asking Groq to build your day-wise curriculum...")

    try:
        instructions = generate_instructions(idea_content)

        # Never trust the model's format blindly: save it, then check it can be parsed.
        instruction_path.write_text(instructions, encoding="utf-8")
        steps = parse_all_steps(instruction_path)
        missing = [s for s in steps if "**Validation:**" not in s["content"]]

        if not steps:
            os.replace(instruction_path, cwd / "INSTRUCTION.raw.md")
            logger.error('The AI reply had no "### Step N" sections, so it cannot be tracked.')
            logger.hint("Saved as INSTRUCTION.raw.md. Run `jibun init` again — the model output varies between runs.")
            return
        if missing:
            nums = ", ".join(str(s["number"]) for s in missing)
            logger.warn(f"Step(s) {nums} have no Validation block and will fail the checker. Consider re-running init.")

        logger.success("Created INSTRUCTION.md")

        days = parse_days(instruction_path)
        save_state(cwd, {
            "currentStep": 0,
            "totalSteps": len(steps),
            "startedAt": iso_now(),
            "projectPath": str(cwd),
            "reviews": {},
        })
        shutil.rmtree(cwd / ".jibun" / "snapshots" / "last-passed", ignore_errors=True)
        n = take_snapshot(cwd, "baseline")  # day reviews diff against this
        logger.success(f"Initialized .jibun/state.json (baseline snapshot: {n} file(s))")

        logger.divider()
        logger.info(f"Curriculum ready: {len(steps)} steps over {len(days)} day(s).")
        for d in days:
            logger.info(f"  Day {d['day']}: {d['title']} (steps {', '.join(map(str, d['steps']))})")
        logger.info("Run: jibun start      (end of a day: jibun review)")
    except Exception as err:
        logger.error("Failed to generate instructions.")
        logger.error(str(err))
        logger.hint("Make sure GROQ_API_KEY is in Jibun/.env and your internet is up.")
