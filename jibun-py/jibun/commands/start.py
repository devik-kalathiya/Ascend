"""Watch mode: validate progress as files change, unlock steps, answer keypresses.

The original Node version juggled callbacks; here the file watcher, the "stuck?" timer and the
keyboard all just post to one main loop, so nothing runs concurrently with anything else.
"""
import os
import re
import sys
import threading
import time
from pathlib import Path

from .. import logger
from ..gate import check_day_gate
from ..hinting import get_hint, print_hint
from ..intervention import (mark_progress, run_intervention, start_intervention_tracker,
                            stop_intervention_tracker)
from ..state import load_state, save_state
from ..validator import get_current_step_content, parse_all_steps, parse_days, validate_all_steps
from ..watcher import start_watcher
from .review import review_day

DEBOUNCE_S = 0.3


class KeyReader:
    """Single-keypress reader (no Enter needed). Does nothing when stdin is not a terminal."""

    def __init__(self):
        self.enabled = sys.stdin.isatty()
        self._old = None

    def __enter__(self):
        if self.enabled and os.name != "nt":
            import termios, tty
            self._fd = sys.stdin.fileno()
            self._old = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)  # keeps Ctrl+C -> SIGINT, unlike full raw mode
        return self

    def __exit__(self, *exc):
        if self._old is not None:
            import termios
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)

    def get(self, timeout: float):
        if not self.enabled:
            time.sleep(timeout)
            return None
        if os.name == "nt":
            import msvcrt
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                if msvcrt.kbhit():
                    return msvcrt.getwch()
                time.sleep(0.02)
            return None
        import select
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return None
        data = os.read(sys.stdin.fileno(), 1)
        return data.decode("utf-8", errors="ignore") or None


class WatchSession:
    def __init__(self, cwd):
        self.cwd = Path(cwd)
        self.instruction_path = self.cwd / "INSTRUCTION.md"
        self.state = load_state(self.cwd)
        self.steps = parse_all_steps(self.instruction_path)
        self.days = parse_days(self.instruction_path)
        self.running = True
        self._debounce_at = None            # monotonic deadline for the next validation
        self._stuck = threading.Event()     # set by the intervention timer thread
        self._observer = None

    # -- display ----------------------------------------------------------

    def show_keyboard_help(self):
        print("")
        logger.info("Keys: [h] hint  [r] re-show step  [d] day review  [q] quit")
        print("")

    def show_current_step(self):
        next_num = self.state["currentStep"] + 1
        step = next((s for s in self.steps if s["number"] == next_num), None)

        gate = check_day_gate(self.cwd, self.days, self.state["currentStep"])
        if gate["locked"]:
            logger.divider()
            logger.warn(f"Day {gate['day']['day']} (\"{gate['day']['title']}\") is locked until "
                        f"Day {gate['previous']['day']} passes its review.")
            logger.hint("Press [d] here (or run `jibun review` in another terminal).")
            logger.divider()
            return

        if not step:
            logger.error(f"Could not find Step {next_num} in INSTRUCTION.md")
            return

        title = re.search(r"###\s*Step\s*\d+[:\s]*(.+)", step["content"])
        what = re.search(r"\*\*What\?\*\*\s*\n(.+)", step["content"])

        logger.divider()
        logger.step(next_num, title.group(1).strip() if title else step["title"])
        if what:
            logger.info(what.group(1).strip())
        logger.divider()

    # -- events -----------------------------------------------------------

    def on_file_event(self, event, file_path):
        try:
            rel = os.path.relpath(file_path, self.cwd)
        except ValueError:
            rel = file_path
        logger.info(f"{event}: {rel}")
        self._debounce_at = time.monotonic() + DEBOUNCE_S

    def handle_key(self, key):
        k = key.lower()
        if k in ("q", "\x03"):
            self.running = False
        elif k == "r":
            self.show_current_step()
        elif k == "d":
            review_day(self.cwd)
            self.state = load_state(self.cwd)
            self.show_current_step()
        elif k == "h":
            self.show_inline_hint()

    def show_inline_hint(self):
        step_num = self.state["currentStep"] + 1
        content = get_current_step_content(self.instruction_path, step_num)
        if not content:
            logger.error(f"Could not find Step {step_num} in INSTRUCTION.md.")
            return
        logger.info("Fetching hint...")
        h = get_hint(content, self.cwd)
        logger.info(f"Hint for Step {step_num}:")
        print_hint(logger, h)
        self.show_keyboard_help()

    def run_stuck_intervention(self):
        step_num = self.state["currentStep"] + 1
        content = get_current_step_content(self.instruction_path, step_num)
        if content:
            run_intervention(content, step_num, self.cwd)

    # -- validation -------------------------------------------------------

    def run_full_validation(self):
        current = self.state["currentStep"]
        results = validate_all_steps([s for s in self.steps if s["number"] <= current + 1], self.cwd)

        # Check for regressions
        regressions = [r for r in results if r["number"] <= current and not r["passed"]]
        if regressions:
            first_broken = min(regressions, key=lambda r: r["number"])
            logger.error("REGRESSION DETECTED — previous step(s) are now incomplete:")
            for r in regressions:
                logger.error(f"  Step {r['number']}: {r['reason']}")

            # AUTO-ROLLBACK: rewind state to before the first broken step
            new_step = first_broken["number"] - 1
            if new_step != current:
                self.state = save_state(self.cwd, {"currentStep": new_step})
                logger.warn(f"State rolled back to Step {new_step + 1}. Fix the regression to continue.")
                self.show_current_step()
            else:
                logger.hint("Fix the missing files/folders before continuing.")
            return  # don't validate the current step while in regression

        gate = check_day_gate(self.cwd, self.days, current)
        if gate["locked"]:
            logger.warn(f"Day {gate['day']['day']} is locked. Pass the Day {gate['previous']['day']} "
                        "review first (press [d] or run `jibun review`).")
            return

        result = next((r for r in results if r["number"] == current + 1), None)
        if not result:
            return

        logger.info("Validating...")
        for c in result["checks"]:
            print(f"   {'✔' if c['exists'] else '✖'}  {c['type']}: {c['target']}")

        if not result["passed"]:
            logger.warn(f"Not yet complete: {result['reason']}")
            return

        logger.success(f"Step {result['number']} completed!")
        self.state = save_state(self.cwd, {"currentStep": current + 1})
        mark_progress()

        if self.state["currentStep"] >= len(self.steps):
            logger.success("All steps completed! 🎉")
            self.running = False
            return

        finished = next((d for d in self.days if result["number"] in d["steps"]), None)
        if finished and finished["steps"][-1] == result["number"]:
            logger.divider()
            logger.success(f"Day {finished['day']} (\"{finished['title']}\") is complete!")
            logger.hint("Press [d] for your day review. It unlocks the next day.")

        logger.info("Loading next step...")
        self.show_current_step()

    # -- main loop --------------------------------------------------------

    def run(self):
        self.show_current_step()
        self.show_keyboard_help()

        start_intervention_tracker(self.instruction_path, self._stuck.set)
        self._observer = start_watcher(self.cwd, self.on_file_event)

        try:
            with KeyReader() as keys:
                while self.running:
                    key = keys.get(0.1)
                    if key:
                        self.handle_key(key)
                    if self._stuck.is_set():
                        self._stuck.clear()
                        self.run_stuck_intervention()
                    if self._debounce_at is not None and time.monotonic() >= self._debounce_at:
                        self._debounce_at = None
                        self.run_full_validation()
        except KeyboardInterrupt:
            pass
        finally:
            self.teardown()

    def teardown(self):
        logger.info("Stopping watcher...")
        stop_intervention_tracker()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None


def start(cwd=None) -> None:
    logger.header("Jibun — Watch Mode")
    cwd = Path(cwd or os.getcwd())

    if load_state(cwd) is None:
        logger.error("No .jibun/state.json found. Run `jibun init` first.")
        return
    if not (cwd / "INSTRUCTION.md").exists():
        logger.error("No INSTRUCTION.md found. Run `jibun init` first.")
        return

    session = WatchSession(cwd)
    if session.state["currentStep"] >= len(session.steps):
        logger.success("All steps completed! 🎉")
        return
    session.run()
