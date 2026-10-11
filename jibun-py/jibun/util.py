"""Small helpers shared by several modules."""
from datetime import datetime, timezone
from pathlib import Path


def iso_now() -> str:
    """UTC timestamp in the same format JavaScript's Date#toISOString() uses."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def read_text(path) -> str:
    """Read a text file leniently (bad bytes are replaced rather than raising)."""
    return Path(path).read_text(encoding="utf-8", errors="replace")
