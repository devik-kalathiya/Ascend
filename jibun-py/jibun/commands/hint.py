import os
from pathlib import Path

from .. import logger
from ..hinting import get_hint, print_hint
from ..state import load_state
from ..validator import get_current_step_content


def hint(cwd=None) -> None:
    logger.header("Jibun — Hint")

    cwd = Path(cwd or os.getcwd())
    instruction_path = cwd / "INSTRUCTION.md"

    state = load_state(cwd)
    if state is None:
        logger.error("No .jibun/state.json found. Run `jibun init` first.")
        return
    if not instruction_path.exists():
        logger.error("No INSTRUCTION.md found. Run `jibun init` first.")
        return

    step_num = state["currentStep"] + 1
    if step_num > state["totalSteps"]:
        logger.success("You have already completed all steps! 🎉")
        return

    logger.info(f"Fetching hint for Step {step_num}...")
    content = get_current_step_content(instruction_path, step_num)
    if not content:
        logger.error(f"Could not find Step {step_num} in INSTRUCTION.md.")
        return

    h = get_hint(content, cwd)
    logger.info(f"Hint for Step {step_num}:")
    print_hint(logger, h)
