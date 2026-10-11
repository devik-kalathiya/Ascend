import os
from pathlib import Path
from typing import Any, Dict, Optional

from .. import logger
from ..gate import default_review_day
from ..review_agent import review_to_markdown, run_review_agent
from ..snapshot import diff_since, has_snapshot, take_snapshot
from ..state import load_state, save_state
from ..util import iso_now
from ..validator import parse_all_steps, parse_days, validate_all_steps
import json


def review_day(project_path, day_number: Optional[int] = None, ack: bool = False) -> Optional[Dict[str, Any]]:
    """Review one day. Reusable from the CLI command and from the `d` key in watch mode.
    Returns {day, review, file} or None."""
    project_path = Path(project_path)
    instruction_path = project_path / "INSTRUCTION.md"
    state = load_state(project_path)

    if not state or not instruction_path.exists():
        logger.error("No Jibun project here. Run `jibun init` first.")
        return None

    days = parse_days(instruction_path)
    all_steps = parse_all_steps(instruction_path)
    if not days:
        logger.error("INSTRUCTION.md has no steps to review.")
        return None

    if day_number is None:
        day = default_review_day(days, state)
    else:
        day = next((d for d in days if d["day"] == day_number), None)
    if not day:
        logger.error(f"Day {day_number} not found. Available days: {', '.join(str(d['day']) for d in days)}")
        return None

    steps = [s for s in all_steps if s["number"] in day["steps"]]
    validation = validate_all_steps(steps, project_path)
    base = "last-passed" if has_snapshot(project_path, "last-passed") else "baseline"
    diff = diff_since(project_path, base)

    logger.info(f"Reviewing Day {day['day']}: {day['title']} ({len(diff['files'])} changed file(s))...")
    review = run_review_agent(day, steps, validation, diff, project_path)

    reviews_dir = project_path / ".jibun" / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    file = reviews_dir / f"day-{day['day']}.md"
    file.write_text(review_to_markdown(day, review), encoding="utf-8")
    (reviews_dir / f"day-{day['day']}.json").write_text(json.dumps(review, indent=2), encoding="utf-8")

    passed = bool(review["ready"] or ack)
    save_state(project_path, {"reviews": {day["day"]: {
        "passed": passed,
        "acknowledged": (not review["ready"]) and ack,
        "score": review["score"],
        "reviewedAt": iso_now(),
        "source": review["source"],
    }}})
    if passed:
        take_snapshot(project_path, "last-passed")

    _print_review(day, review, passed, file, ack and not review["ready"], project_path)
    return {"day": day, "review": review, "file": file}


def _print_review(day, review, passed, file, acknowledged, project_path) -> None:
    logger.divider()
    logger.header(f"Day {day['day']} Review — {day['title']}")
    if review["source"] == "offline":
        logger.warn(f"AI reviewer unavailable ({review.get('fallbackReason')}). Using the offline checker.")

    print(review["summary"])
    print("")
    if review["notes"]:
        logger.info("Notes:")
        for n in review["notes"]:
            print(f"   • {n}")

    if review["mistakes"]:
        print("")
        logger.warn("Mistakes:")
        for i, m in enumerate(review["mistakes"]):
            print(f"   {i + 1}. [{m['severity']}] {m['file']} — {m['issue']}")
            for s in (s for s in review["solutions"] if s["mistake"] == i):
                print(f"      ↳ hint: {s['hint']}")
                for d in s["docs"]:
                    print(f"        {d}")
    else:
        logger.success("No mistakes found.")

    print("")
    logger.info(f"Score: {review['score']}/100")
    if review["next_focus"]:
        logger.hint(f"Next focus: {review['next_focus']}")
    try:
        shown = os.path.relpath(file, project_path)
    except ValueError:
        shown = str(file)
    logger.info(f"Saved: {shown}")
    logger.divider()

    if passed:
        logger.success(f"Day {day['day']} acknowledged. Next day unlocked." if acknowledged
                       else f"Day {day['day']} passed. Next day unlocked! 🎉")
    else:
        logger.warn(f"Day {day['day']} not passed yet. Fix the mistakes above and run `jibun review` again "
                    "(or `jibun review --ack` to move on anyway).")


def review(day: Optional[int] = None, ack: bool = False, cwd=None) -> None:
    logger.header("Jibun — Day Review")
    review_day(cwd or os.getcwd(), day_number=day, ack=ack)
