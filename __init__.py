#!/usr/bin/env python3

import sys
from types import SimpleNamespace

import cloup
from cloup import Context, HelpFormatter, HelpTheme, Style
from rich.console import Console

from nyaaup.auth import auth
from nyaaup.up import up
from nyaaup.utils import DefaultCommandGroup
from nyaaup.utils.decorators import command_header

console = Console()

CONTEXT_SETTINGS = Context.settings(
    help_option_names=["-h", "--help"],
    max_content_width=116,
    align_option_groups=False,
    align_sections=True,
    formatter_settings=HelpFormatter.settings(
        indent_increment=3,
        col1_max_width=50,
        col_spacing=3,
        theme=HelpTheme(
            section_help=Style(fg="bright_white", bold=True),
            command_help=Style(fg="bright_white", bold=True),
            invoked_command=Style(fg="cyan"),
            heading=Style(fg="yellow", bold=True),
            col1=Style(fg="green"),
            col2=Style(fg="bright_white", bold=True),
        ),
    ),
)


@cloup.group(
    cls=DefaultCommandGroup,
    context_settings=CONTEXT_SETTINGS,
)
@command_header
@cloup.pass_context
def main(ctx, **kwargs):
    """Nyaaup - Auto torrent uploader to Nyaa"""
    if any(x in sys.argv for x in ctx.help_option_names):
        return

    args = SimpleNamespace(**kwargs)
    ctx.obj = args


main.add_command(auth)
main.add_command(up)

if __name__ == "__main__":
    main()