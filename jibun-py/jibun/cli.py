"""Command line entry point:  jibun init | start | hint | review | status"""
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from . import __version__


def _load_env() -> None:
    # Same as the original: <tool root>/.env first; a .env in the project folder also works.
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    load_dotenv(Path.cwd() / ".env")


@click.group(help="The Senior Dev Learning Companion")
@click.version_option(__version__, prog_name="jibun")
def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # box/emoji output on Windows
        except Exception:
            pass
    _load_env()


@main.command("init", help="Read IDEA.md and generate the day-wise INSTRUCTION.md")
@click.option("--force", is_flag=True, help="regenerate even if you already have progress")
def init_cmd(force):
    from .commands.init import init
    init(force=force)


@main.command("start", help="Start watch mode: validate progress and unlock steps")
def start_cmd():
    from .commands.start import start
    start()


@main.command("hint", help="Get a hint when you are stuck on the current step")
def hint_cmd():
    from .commands.hint import hint
    hint()


@main.command("review", help="Day review: notes, mistakes and solution hints for what you built")
@click.option("-d", "--day", type=int, default=None, help="review a specific day (default: current day)")
@click.option("--ack", is_flag=True, help="acknowledge the review and unlock the next day even if it did not pass")
def review_cmd(day, ack):
    from .commands.review import review
    review(day=day, ack=ack)


@main.command("status", help="Show progress per day and review results")
def status_cmd():
    from .commands.status import status
    status()


if __name__ == "__main__":
    main()
