#!/usr/bin/env python3
from .utils import RParse
from .nyaaup import Nyaasi
from .auth import Auth
from .__init__ import __version__

import argparse
import sys
from pathlib import Path
from rich.traceback import install
from rich.console import Console

console = Console()
install(show_locals=True)


def main():
    console.print(
        f"[b]nyaaup[/b] [magenta bold]v{__version__}[/]\n\n[dim]Auto torrent uploader to Nyaa.si\n",  # noqa: E501
        justify="center",
    )

    parser = argparse.ArgumentParser(
        description='Auto torrent uploader to Nyaa.si', prog='nyaaup')
    parser = RParse()
    subparsers = parser.add_subparsers(dest="command", required=True)
    parser_auth = subparsers.add_parser("auth")
    parser_auth.add_argument(
        '-add', '--add-credential',
        type=str,
        metavar="USER:PASS",
        default=None,
        help="Add or replace credential in config file."
    )
    parser_up = subparsers.add_parser("up")
    parser_up.add_argument(
        '-ch', '--category-help',
        action='store_true',
        help='Print available categories.'
    )
    parser_up.add_argument(
        '-ms', '--multi-subs',
        action='store_true',
        help='Add Multi Subs tag to title.'
    )
    parser_up.add_argument(
        '-da', '--dual-audios',
        action='store_true',
        help='Add Dual audios tag to title.'
    )
    parser_up.add_argument(
        '-ma', '--multi-audios',
        action='store_true',
        help='Add Multi audios tag to title.'
    )
    parser_up.add_argument(
        '-a', '--auto',
        action='store_true',
        help='Detect multi subs, multi audios and dual audios.'
    )
    parser_up.add_argument(
        '-A', '--anonymous',
        action='store_true',
        help='Upload torrent as anonymous.'
    )
    parser_up.add_argument(
        '-H', '--hidden',
        action='store_true',
        help='Upload the torrent as hidden.'
    )
    parser_up.add_argument(
        '-C', '--complete',
        action='store_true',
        help='If the torrnet is a complete batch.'
    )
    parser_up.add_argument(
        '-s', '--skip-upload',
        action='store_true',
        help='Skip torrent upload.'
    )
    parser_up.add_argument(
        '-e', '--edit-code',
        type=str,
        default=None,
        help='Use uniq edit code for mediainfo on rentry.co'
    )
    parser_up.add_argument(
        '-p', '--pictures-number',
        type=int,
        default=3,
        help='Number of picture to upload to the torrent (default: 3).'
    ),
    parser_up.add_argument(
        '-n', '--note',
        type=str,
        default=None,
        help='Put a note in to the description.'
    ),
    parser_up.add_argument(
        '-M', '--no-mediainfo',
        action='store_true',
        help='Do not attach mediainfo to the torrent (provider rentry.co).'
    )
    parser_up.add_argument(
        '-m', '--myanimelist',
        type=str,
        default=None,
        help='MyAnimeList link.'
    )
    parser_up.add_argument(
        '--skip-myanimelist',
        action='store_true',
        help='Skip anything that connect to MyAnimeList (in case of downtime).'
    )
    parser_up.add_argument(
        '-c', '--category',
        type=str,
        default=None,
        help='Select a category, for help use: --category-help (1-6).'
    )
    parser_up.add_argument(
        '-o', '--overwrite',
        action='store_true',
        help='Recreate the .torrent if it already exists.'
    )
    parser_up.add_argument(
        "path",
        type=Path,
        nargs="*",
        default=None,
        help="File or directory to upload."
    )
    parser.set_defaults(default_command=True, command='up')
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()

    if args.command == "auth":
        Auth(args, parser)
    else:
        Nyaasi(args, parser)


if __name__ == "__main__":
    main()
