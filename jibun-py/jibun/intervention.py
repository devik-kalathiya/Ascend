"""Auto-hint when the learner has been stuck on a step for too long."""
import os
import threading
import time
from typing import Callable, Optional

from . import logger
from .config import STUCK_THRESHOLD_MS
from .hinting import get_hint, print_hint

CHECK_INTERVAL_S = 60

_thread: Optional[threading.Thread] = None
_stop = threading.Event()
_last_progress = time.monotonic()
_last_intervention = 0.0
_is_running = False


def start_intervention_tracker(instruction_path, on_intervention: Callable[[], None],
                               check_interval_s: float = CHECK_INTERVAL_S) -> None:
    """Calls `on_intervention()` (from a background thread) when no progress was made for
    STUCK_THRESHOLD_MS, at most once per threshold period."""
    global _thread, _last_progress, _last_intervention, _is_running
    if _is_running:
        return
    _is_running = True
    _last_progress = time.monotonic()
    _last_intervention = -STUCK_THRESHOLD_MS  # "never": the first check may fire
    _stop.clear()
    threshold = STUCK_THRESHOLD_MS / 1000

    def loop():
        global _last_intervention
        while not _stop.wait(check_interval_s):
            now = time.monotonic()
            if now - _last_progress > threshold and now - _last_intervention > threshold:
                _last_intervention = now
                if callable(on_intervention):
                    on_intervention()

    _thread = threading.Thread(target=loop, name="jibun-intervention", daemon=True)
    _thread.start()


def mark_progress() -> None:
    global _last_progress
    _last_progress = time.monotonic()


def stop_intervention_tracker() -> None:
    global _thread, _is_running
    _stop.set()
    _thread = None
    _is_running = False


def run_intervention(step_content: str, step_number: int, project_path=None) -> None:
    logger.divider()
    logger.warn("You have been on this step for a while. Let me help you out...")
    logger.info("Thinking...")
    h = get_hint(step_content, project_path or os.getcwd())
    logger.info(f"Auto-hint for Step {step_number}:")
    print_hint(logger, h)
