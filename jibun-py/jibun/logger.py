"""Coloured console output (the chalk-based logger of the original)."""
import os
import sys

from colorama import Fore, Style, just_fix_windows_console

just_fix_windows_console()

_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _c(color: str, text: str, bold: bool = False) -> str:
    if not _COLOR:
        return text
    return f"{Style.BRIGHT if bold else ''}{color}{text}{Style.RESET_ALL}"


def info(msg):    print(_c(Fore.BLUE, "ℹ "), _c(Fore.WHITE, msg))
def success(msg): print(_c(Fore.GREEN, "✔ "), _c(Fore.WHITE, msg))
def warn(msg):    print(_c(Fore.YELLOW, "⚠ "), _c(Fore.WHITE, msg))
def error(msg):   print(_c(Fore.RED, "✖ "), _c(Fore.WHITE, msg))
def hint(msg):    print(_c(Fore.MAGENTA, "💡 "), _c(Fore.WHITE, msg))
def step(num, title): print(_c(Fore.CYAN, f"\n▸ Step {num}: {title}"))
def divider():    print(_c(Fore.LIGHTBLACK_EX, "─" * 50))


def header(text):
    print("")
    print(_c(Fore.WHITE, text, bold=True))
    print(_c(Fore.LIGHTBLACK_EX, "─" * 50))
