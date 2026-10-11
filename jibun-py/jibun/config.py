"""Single place for settings that used to be hard-coded across files."""
import os
import re

DEFAULT_MODEL = "openai/gpt-oss-120b"
MAX_RETRIES = 3
BASE_DELAY_MS = 2000
STUCK_THRESHOLD_MS = 10 * 60 * 1000


def get_model() -> str:
    """Read lazily so a value from .env (loaded at start-up) is honoured."""
    return os.environ.get("JIBUN_MODEL") or DEFAULT_MODEL


# Files/folders that are never part of the learner's work.
IGNORED_DIRS = ["node_modules", ".jibun", ".git", "dist", "build", "coverage"]
IGNORED_FILES = ["INSTRUCTION.md", "INSTRUCTION.raw.md", "IDEA.md", "package-lock.json"]
TEXT_EXT = re.compile(r"\.(js|mjs|cjs|html|css|json|md|txt|ts|jsx|tsx|yml|yaml|env)$", re.I)
