import sys
from typing import Literal, NoReturn, overload

from rich.console import Console
from rich.padding import Padding


def _get_console(highlight: bool = False) -> Console:
    return Console(highlight=highlight)


@overload
def eprint(text: str, fatal: Literal[False] = False, exit_code: int = 1) -> None: ...


@overload
def eprint(text: str, fatal: Literal[True], exit_code: int = 1) -> NoReturn: ...


def eprint(text: str, fatal: bool = False, exit_code: int = 1) -> None | NoReturn:
    if text.startswith("\n"):
        text = text.lstrip("\n")
        print()
    _get_console().print(f"[bold color(231) on red]ERROR:[/] [red]{text}[/]")
    if fatal:
        sys.exit(exit_code)
    return None


def iprint(text: str, up: int = 1, down: int = 1) -> None:
    _get_console().print(Padding(f"[bold green]{text}[white]", (up, 0, down, 0), expand=False))


def wprint(text: str) -> None:
    if text.startswith("\n"):
        text = text.lstrip("\n")
        print()
    _get_console().print(f"[bold color(231) on yellow]WARNING:[/] [yellow]{text}[/]")
