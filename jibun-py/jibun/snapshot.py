"""Snapshots of the learner's files, so a day review can show what changed."""
import difflib
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

from .config import IGNORED_DIRS, IGNORED_FILES, TEXT_EXT
from .util import read_text
from .validator import get_all_files

MAX_FILE_BYTES = 100 * 1024


def _snap_dir(project_path, label: str) -> Path:
    return Path(project_path) / ".jibun" / "snapshots" / label


def list_work_files(project_path) -> List[str]:
    """Text files that belong to the learner's work (relative, forward-slash paths)."""
    root = Path(project_path)
    out = []
    for f in get_all_files(root, IGNORED_DIRS):
        rel = f.relative_to(root).as_posix()
        if (TEXT_EXT.search(rel) and os.path.basename(rel) not in IGNORED_FILES
                and not rel.startswith(".") and f.stat().st_size <= MAX_FILE_BYTES):
            out.append(rel)
    return out


def has_snapshot(project_path, label: str) -> bool:
    return _snap_dir(project_path, label).exists()


def take_snapshot(project_path, label: str) -> int:
    """Copy the learner's current files into .jibun/snapshots/<label>/ (replacing any old one)."""
    d = _snap_dir(project_path, label)
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    files = list_work_files(project_path)
    for rel in files:
        dest = d / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(project_path) / rel, dest)
    return len(files)


def _read_snapshot_files(project_path, label: str) -> Dict[str, str]:
    d = _snap_dir(project_path, label)
    if not d.exists():
        return {}
    return {f.relative_to(d).as_posix(): read_text(f) for f in get_all_files(d, [])}


def _count_lines(text: str) -> int:
    return len(text.split("\n")) if text else 0


def diff_since(project_path, base_label: str) -> Dict[str, Any]:
    """What changed in the project since snapshot `base_label` (or since nothing, if it does not exist).
    Returns {files: [{path, status, added, removed, patch}], totalAdded, totalRemoved}."""
    before = _read_snapshot_files(project_path, base_label)
    now = list_work_files(project_path)
    files: List[Dict[str, Any]] = []

    for rel in now:
        after = read_text(Path(project_path) / rel)
        old = before.get(rel)
        if old == after:
            continue

        lines = list(difflib.unified_diff(
            (old or "").splitlines(), after.splitlines(),
            fromfile=rel, tofile=rel,
            fromfiledate="new file" if old is None else "before", tofiledate="now",
            n=2, lineterm=""))
        body = lines[2:]  # skip the ---/+++ header when counting
        added = sum(1 for l in body if l.startswith("+"))
        removed = sum(1 for l in body if l.startswith("-"))
        files.append({"path": rel, "status": "added" if old is None else "modified",
                      "added": added, "removed": removed, "patch": "\n".join(lines)})

    for rel, text in before.items():
        if rel not in now:
            files.append({"path": rel, "status": "deleted", "added": 0,
                          "removed": _count_lines(text), "patch": f"(deleted {rel})"})

    return {"files": files,
            "totalAdded": sum(f["added"] for f in files),
            "totalRemoved": sum(f["removed"] for f in files)}
