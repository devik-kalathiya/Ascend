"""The Review Agent: looks at what the learner changed during a day (a diff), the day's steps
and the validator results, and writes a mentor-style review: notes (what they built),
mistakes, and solutions (hints, never full code)."""
import math
import re
from pathlib import Path
from typing import Any, Callable, Dict, List

from .llm import chat, extract_json
from .prompts import REVIEW_SYSTEM_PROMPT
from .util import iso_now, read_text

MAX_DIFF_CHARS = 12000


def build_review_prompt(day, steps, validation, diff) -> str:
    step_text = "\n\n---\n\n".join(s["content"] for s in steps)
    checks = "\n".join(
        f"Step {v['number']} \"{v['title']}\": " + ("PASSED" if v["passed"] else "FAILED — " + v["reason"])
        for v in validation)

    diff_text = "\n\n".join(
        f"### {f['status'].upper()}: {f['path']} (+{f['added']} -{f['removed']})\n{f['patch']}"
        for f in diff["files"])
    if len(diff_text) > MAX_DIFF_CHARS:
        diff_text = diff_text[:MAX_DIFF_CHARS] + "\n…(diff truncated)"

    return (f"DAY {day['day']}: {day['title']}\n\n"
            f"STEPS FOR THIS DAY:\n{step_text}\n\n"
            f"AUTOMATIC VALIDATION RESULTS:\n{checks or '(none)'}\n\n"
            f"WHAT THE LEARNER CHANGED TODAY (diff):\n{diff_text or '(no changes detected)'}")


# ---------------------------------------------------------------------------
#  Offline review (no API): validator results + simple code smells
# ---------------------------------------------------------------------------

_MDN = "https://developer.mozilla.org/en-US/docs/Web/"

SMELLS: List[Dict[str, Any]] = [
    {"re": re.compile(r"\bconsole\.log\("), "min": 4, "severity": "low",
     "issue": lambda n: f"{n} console.log calls are left in the code. Debug output should be removed or replaced with real error handling.",
     "hint": "Decide which logs help you debug today and which can go. Keep errors in console.error inside catch blocks.",
     "docs": [_MDN + "API/console"]},
    {"re": re.compile(r"\b(TODO|FIXME)\b"), "min": 1, "severity": "low",
     "issue": lambda n: f"{n} TODO/FIXME comment(s) are still open.",
     "hint": "Either finish them while the context is fresh or note them for tomorrow's plan.",
     "docs": []},
    {"re": re.compile(r"(^|\s)var\s+\w+"), "min": 1, "severity": "low",
     "issue": lambda n: f"`var` is used {n} time(s). It is function-scoped and hoisted, which causes surprising bugs.",
     "hint": "Think about which variables change later (let) and which never do (const).",
     "docs": [_MDN + "JavaScript/Reference/Statements/let"]},
    {"re": re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}"), "min": 1, "severity": "medium",
     "issue": lambda n: "An empty catch block swallows errors silently, which makes bugs hard to find.",
     "hint": "What should the user (or you) see if this operation fails?",
     "docs": [_MDN + "JavaScript/Reference/Statements/try...catch"]},
    {"re": re.compile(r"innerHTML\s*[+]?=\s*[^;\n]*(\+|\$\{)"), "min": 1, "severity": "medium",
     "issue": lambda n: "innerHTML is assigned from a built string. If any part comes from user input this allows script injection.",
     "hint": "Compare how textContent and document.createElement treat the same input.",
     "docs": [_MDN + "API/Element/innerHTML#security_considerations"]},
]


def heuristic_review(day, validation, diff, project_path, **_) -> Dict[str, Any]:
    mistakes: List[Dict[str, Any]] = []
    solutions: List[Dict[str, Any]] = []

    for v in (v for v in validation if not v["passed"]):
        mistakes.append({"file": "general", "severity": "high",
                         "issue": f"Step {v['number']} \"{v['title']}\" is not complete. {v['reason']}"})
        solutions.append({"mistake": len(mistakes) - 1,
                          "hint": 'Re-read the "How?" and "Validation" parts of this step and compare them with your files.',
                          "docs": []})

    for f in (f for f in diff["files"] if f["status"] != "deleted" and re.search(r"\.(js|mjs|html)$", f["path"])):
        try:
            text = read_text(Path(project_path) / f["path"])
        except OSError:
            continue
        for smell in SMELLS:
            n = len(smell["re"].findall(text))
            if n >= smell["min"]:
                mistakes.append({"file": f["path"], "severity": smell["severity"], "issue": smell["issue"](n)})
                solutions.append({"mistake": len(mistakes) - 1, "hint": smell["hint"], "docs": smell["docs"]})

    failed = sum(1 for v in validation if not v["passed"])
    non_high = sum(1 for m in mistakes if m["severity"] != "high")
    if validation:
        score = max(0, math.floor(100 * (len(validation) - failed) / len(validation) + 0.5) - 3 * non_high)
    else:
        score = 0

    return {
        "summary": (f"Offline review of Day {day['day']} ({day['title']}): {len(validation) - failed}/{len(validation)} "
                    f"steps pass the automatic checks. You changed {len(diff['files'])} file(s) "
                    f"(+{diff['totalAdded']} / -{diff['totalRemoved']} lines)."),
        "notes": [f"{f['status']} {f['path']} (+{f['added']} -{f['removed']})" for f in diff["files"][:5]],
        "mistakes": mistakes,
        "solutions": solutions,
        "score": score,
        "next_focus": ("Finish the unfinished steps before starting the next day." if failed
                       else "Continue with the next day's plan."),
        "source": "offline",
    }


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------


def _is_int(v) -> bool:
    return (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, float) and v.is_integer())


def _num(v) -> float:
    try:
        return float(v) or 0
    except (TypeError, ValueError):
        return 0


def normalise(raw: Dict[str, Any]) -> Dict[str, Any]:
    arr: Callable[[Any], list] = lambda v: v if isinstance(v, list) else []
    mistakes = [
        {"file": m.get("file") or "general",
         "severity": m["severity"] if m.get("severity") in ("high", "medium", "low") else "medium",
         "issue": str(m["issue"])}
        for m in arr(raw.get("mistakes")) if isinstance(m, dict) and m.get("issue")
    ]
    solutions = [
        {"mistake": int(s["mistake"]) if _is_int(s.get("mistake")) else -1,
         "hint": str(s["hint"]),
         "docs": [str(d) for d in arr(s.get("docs"))]}
        for s in arr(raw.get("solutions")) if isinstance(s, dict) and s.get("hint")
    ]
    return {
        "summary": str(raw.get("summary") or ""),
        "notes": [str(n) for n in arr(raw.get("notes"))],
        "mistakes": mistakes,
        "solutions": solutions,
        "score": int(max(0, min(100, _num(raw.get("score"))))),
        "next_focus": str(raw.get("next_focus") or ""),
    }


def run_review_agent(day, steps, validation, diff, project_path) -> Dict[str, Any]:
    """Returns the review plus `ready` (computed locally, never trusted from the model) and `source`."""
    try:
        raw = chat(system=REVIEW_SYSTEM_PROMPT, user=build_review_prompt(day, steps, validation, diff),
                   json_mode=True, temperature=0.4, max_tokens=2000)
        review = {**normalise(extract_json(raw)), "source": "ai"}
    except Exception as err:
        review = {**heuristic_review(day, validation, diff, project_path), "fallbackReason": str(err)}

    all_pass = all(v["passed"] for v in validation)
    has_high = any(m["severity"] == "high" for m in review["mistakes"])
    review["ready"] = all_pass and not has_high
    return review


def review_to_markdown(day, review, meta=None) -> str:
    meta = meta or {}
    reviewer = "AI mentor" if review["source"] == "ai" else "offline checker"
    verdict = "PASSED" if review["ready"] else "NOT PASSED YET"
    lines = [f"# Day {day['day']} Review — {day['title']}", "",
             f"*{meta.get('date') or iso_now()} · reviewer: {reviewer} · score: {review['score']}/100 · {verdict}*", "",
             "## Summary", "", review["summary"] or "(none)", "",
             "## Notes (what you built)", ""]
    lines += [f"- {n}" for n in review["notes"]] if review["notes"] else ["- (nothing to note)"]
    lines += ["", "## Mistakes", ""]
    if not review["mistakes"]:
        lines.append("None found. 🎉")
    for i, m in enumerate(review["mistakes"]):
        lines.append(f"{i + 1}. **[{m['severity']}]** `{m['file']}` — {m['issue']}")
    lines += ["", "## Solutions (hints, not answers)", ""]
    if not review["solutions"]:
        lines.append("Nothing to fix.")
    for s in review["solutions"]:
        label = f"Mistake {s['mistake'] + 1}" if s["mistake"] >= 0 else "General"
        lines.append(f"- **{label}:** {s['hint']}")
        lines += [f"  - {d}" for d in s["docs"]]
    lines += ["", "## Next focus", "", review["next_focus"] or "(none)", ""]
    return "\n".join(lines)
