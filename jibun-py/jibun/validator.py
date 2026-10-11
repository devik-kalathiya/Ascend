"""Parse INSTRUCTION.md into steps/days and check the learner's files against each step."""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import IGNORED_DIRS, TEXT_EXT
from .util import read_text

# ---------------------------------------------------------------------------
#  Parsing INSTRUCTION.md
# ---------------------------------------------------------------------------


def _cut_at_next_day(text: str) -> str:
    """A step ends where the next "## ..." (not "### ...") heading begins."""
    m = re.search(r"\n##\s+(?!#)", text)
    return (text[:m.start()] if m else text).strip()


def parse_all_steps(instruction_path) -> List[Dict[str, Any]]:
    content = read_text(instruction_path)
    matches = list(re.finditer(r"###\s*Step\s*(\d+)[:\s]*(.+)", content))
    steps = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        steps.append({
            "number": int(m.group(1)),
            "title": m.group(2).strip(),
            "content": _cut_at_next_day(content[m.start():end]),
        })
    return steps


def get_current_step_content(instruction_path, step_number: int) -> Optional[str]:
    for s in parse_all_steps(instruction_path):
        if s["number"] == step_number:
            return s["content"]
    return None


def parse_days(instruction_path) -> List[Dict[str, Any]]:
    """Day-wise view of the curriculum: [{index, day, title, steps: [1,2,3]}].
    Uses "## Day N: Title" headings. If the model forgot them, steps are grouped 3 per day."""
    content = read_text(instruction_path)
    steps = parse_all_steps(instruction_path)
    heads = list(re.finditer(r"^##\s*Day\s*(\d+)\s*[:\-–]?\s*(.*)$", content, re.I | re.M))

    if not heads:
        days = []
        for i in range(0, len(steps), 3):
            last = steps[min(i + 2, len(steps) - 1)]["number"]
            days.append({
                "index": len(days),
                "day": len(days),
                "title": f"Steps {steps[i]['number']}-{last}",
                "steps": [s["number"] for s in steps[i:i + 3]],
            })
        return days

    days = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(content)
        block = content[h.start():end]
        nums = [int(n) for n in re.findall(r"###\s*Step\s*(\d+)", block)]
        days.append({
            "index": i,
            "day": int(h.group(1)),
            "title": h.group(2).strip() or f"Day {h.group(1)}",
            "steps": nums,
        })
    return [d for d in days if d["steps"]]


def day_of_step(days, step_number: int):
    return next((d for d in days if step_number in d["steps"]), None)


# ---------------------------------------------------------------------------
#  Reading the "Validation:" block
# ---------------------------------------------------------------------------

FILE_LIKE = re.compile(
    r"^(?:[\w@.\-]+/)*[\w@.\-]+\.(?:html|css|js|mjs|cjs|json|md|txt|env|png|jpg|jpeg|svg|ico|ts|tsx|jsx|yml|yaml)$",
    re.I)
CONTAINS_RE = re.compile(
    r"\b(?:contains|includes|has|uses|calls|defines)\s+(?:the\s+)?"
    r"(?:text\s+|string\s+|keyword\s+|function\s+)?`([^`]+)`", re.I)
USED_RE = re.compile(r"`([^`]+)`\s+is\s+used", re.I)


def _is_path_like(item: str) -> bool:
    if " " in item or item.startswith("npm "):
        return False
    return item.endswith("/") or "/" in item or bool(FILE_LIKE.match(item))


def parse_requirements(validation_text: str) -> List[Dict[str, Any]]:
    """Turn the Validation text into a list of {kind, target, scope?} requirements."""
    body = re.sub(r"\*\*Validation:\*\*", "", validation_text, flags=re.I)
    body = re.sub(r"Jibun checks for:", "", body, flags=re.I)

    reqs: List[Dict[str, Any]] = []
    last_file: Optional[str] = None

    for clause in body.split("&&"):
        terms: List[str] = []
        rest = clause

        for rx in (CONTAINS_RE, USED_RE):
            for m in rx.finditer(clause):
                terms.append(m.group(1))
                rest = rest.replace(m.group(0), " ", 1)

        wants_dir = bool(re.search(r"\b(folder|directory)\b", rest, re.I))
        items = [m.group(1).strip() for m in re.finditer(r"`([^`]+)`", rest)]
        clause_file: Optional[str] = None

        for item in items:
            if not _is_path_like(item) and not (wants_dir and " " not in item):
                continue
            if item.endswith("/") or (wants_dir and not FILE_LIKE.match(item)):
                reqs.append({"kind": "directory", "target": item if item.endswith("/") else item + "/"})
            else:
                reqs.append({"kind": "file", "target": item})
                clause_file = item

        if clause_file:
            last_file = clause_file
        for term in terms:
            reqs.append({"kind": "contains", "target": term, "scope": clause_file or last_file})

    return reqs


# ---------------------------------------------------------------------------
#  Quality checks on a file that exists
# ---------------------------------------------------------------------------


def _scan_brackets(source: str) -> Optional[str]:
    """Pure-Python fallback when Node is not installed: are (), [] and {} balanced?
    Strings, template literals, comments and (heuristically) regex literals are skipped."""
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: List[str] = []
    i, n = 0, len(source)
    prev = ""  # last significant character, used to tell "/" division from a regex start

    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""

        if ch == "/" and nxt == "/":
            while i < n and source[i] != "\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":
            end = source.find("*/", i + 2)
            if end == -1:
                return "unterminated comment"
            i = end + 2
            continue
        if ch in "\"'`":
            quote, i = ch, i + 1
            while i < n and source[i] != quote:
                if source[i] == "\\":
                    i += 1
                elif quote != "`" and source[i] == "\n":
                    return "unterminated string"
                i += 1
            if i >= n:
                return "unterminated string"
            i += 1
            prev = quote
            continue
        if ch == "/" and (prev == "" or prev in "(,=:[!&|?{};+-*%<>~^"):
            i += 1  # regex literal
            in_class = False
            while i < n and source[i] != "\n":
                if source[i] == "\\":
                    i += 1
                elif source[i] == "[":
                    in_class = True
                elif source[i] == "]":
                    in_class = False
                elif source[i] == "/" and not in_class:
                    break
                i += 1
            i += 1
            prev = "/"
            continue

        if ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack or stack.pop() != pairs[ch]:
                return f"unexpected '{ch}'"
        if not ch.isspace():
            prev = ch
        i += 1

    return f"unclosed '{stack[-1]}'" if stack else None


def _node_check(source: str, suffix: str) -> Optional[str]:
    """`node --check` compiles a file without running it. Returns an error line, "" if fine."""
    tmpdir = tempfile.mkdtemp(prefix="jibun-")
    try:
        tmp = os.path.join(tmpdir, "check" + suffix)
        Path(tmp).write_text(source, encoding="utf-8")
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True, timeout=15)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    if r.returncode == 0:
        return ""
    line = next((l for l in (r.stderr or "").splitlines() if "SyntaxError" in l), None)
    return re.sub(r"^.*SyntaxError:\s*", "", line) if line else "syntax error"


def js_syntax_error(source: str) -> Optional[str]:
    if shutil.which("node"):
        try:
            err = _node_check(source, ".cjs")  # classic script first
            if err == "":
                return None
            if not re.search(r"import|export", err):
                return err
            err = _node_check(source, ".mjs")  # ES module syntax
            return None if err == "" else err
        except (OSError, subprocess.SubprocessError):
            pass  # fall through to the pure-Python check
    return _scan_brackets(source)


def css_balance_error(source: str) -> Optional[str]:
    clean = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    clean = re.sub(r"([\"'])(?:\\.|(?!\1).)*\1", "", clean)
    opened, closed = clean.count("{"), clean.count("}")
    return None if opened == closed else f"unbalanced braces ({{ {opened} vs }} {closed})"


PAIRED_TAGS = ["div", "section", "ul", "ol", "table", "form", "main", "header", "footer",
               "nav", "script", "style", "body", "html", "button", "canvas"]


def html_structure_error(source: str) -> Optional[str]:
    clean = re.sub(r"<!--.*?-->", "", source, flags=re.S)
    for tag in PAIRED_TAGS:
        opened = len(re.findall(rf"<{tag}(?=[\s>/])", clean, re.I))
        closed = len(re.findall(rf"</{tag}\s*>", clean, re.I))
        if opened != closed:
            return f"<{tag}> opened {opened}x but closed {closed}x"
    return None


def check_file_quality(abs_path) -> Optional[str]:
    """Returns an error string, or None if the file looks fine."""
    ext = Path(abs_path).suffix.lower()
    try:
        source = read_text(abs_path)
    except OSError:
        return None
    if ext not in (".js", ".mjs", ".cjs", ".json", ".css", ".html"):
        return None
    if source.strip() == "":
        return "file is empty"

    if ext == ".json":
        try:
            json.loads(source)
            return None
        except ValueError as e:
            return f"invalid JSON ({e})"
    if ext == ".css":
        return css_balance_error(source)
    if ext == ".html":
        return html_structure_error(source)
    return js_syntax_error(source)


# ---------------------------------------------------------------------------
#  Validation
# ---------------------------------------------------------------------------


def validate_step(step_content: str, project_path) -> Dict[str, Any]:
    block = re.search(r"\*\*Validation:\*\*.*?(?=\n### |\n## |\Z)", step_content, re.S)
    if not block:
        return {"passed": False, "checks": [], "reason": "No validation criteria found in this step."}

    project = Path(project_path)
    reqs = parse_requirements(block.group(0))
    checks: List[Dict[str, Any]] = []

    if not reqs:
        checks.append({"type": "manual", "target": "no automatic checks could be read for this step", "exists": True})

    checked_quality = set()

    for req in reqs:
        if req["kind"] == "directory":
            ok = (project / req["target"]).is_dir()
            checks.append({"type": "directory", "target": req["target"], "exists": ok})
            continue

        if req["kind"] == "file":
            p = project / req["target"]
            ok = p.is_file()
            checks.append({"type": "file", "target": req["target"], "exists": ok})
            if ok and req["target"] not in checked_quality:
                checked_quality.add(req["target"])
                problem = check_file_quality(p)
                if problem:
                    checks.append({"type": "quality", "target": f"{req['target']}: {problem}", "exists": False})
            continue

        # contains: look in the file it belongs to, otherwise anywhere in the project
        scope = req.get("scope")
        found = _file_contains(project / scope, req["target"]) if scope else _search_in_project(project, req["target"])
        where = f" in {scope}" if scope else ""
        checks.append({"type": "contains", "target": f"{req['target']}{where}", "exists": found})

    failed = [c for c in checks if not c["exists"]]
    return {
        "passed": not failed,
        "checks": checks,
        "reason": "All validation criteria met." if not failed
        else "Missing: " + ", ".join(f"{f['type']}:{f['target']}" for f in failed),
    }


def validate_all_steps(steps, project_path) -> List[Dict[str, Any]]:
    return [{"number": s["number"], "title": s["title"], **validate_step(s["content"], project_path)}
            for s in steps]


# ---------------------------------------------------------------------------
#  File helpers
# ---------------------------------------------------------------------------


def _file_contains(abs_path, term: str) -> bool:
    try:
        p = Path(abs_path)
        if p.is_dir():
            return _search_in_project(p, term)
        return term in read_text(p)
    except OSError:
        return False


def _search_in_project(project_path, term: str) -> bool:
    for f in get_all_files(project_path, IGNORED_DIRS):
        if not TEXT_EXT.search(str(f)):
            continue
        try:
            if term in read_text(f):
                return True
        except OSError:
            pass  # unreadable file: skip
    return False


def get_all_files(directory, exclude=IGNORED_DIRS) -> List[Path]:
    results: List[Path] = []
    try:
        for name in sorted(os.listdir(directory)):
            if name in exclude:
                continue
            full = Path(directory) / name
            if full.is_dir():
                results.extend(get_all_files(full, exclude))
            else:
                results.append(full)
    except OSError:
        pass  # directory vanished: ignore
    return results
