#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path


from rich.traceback import install
from rich.console import Console

from nyaaup.utils import RParse
from nyaaup.upload import Upload
from nyaaup.auth import Auth
from nyaaup import __version__


install(show_locals=True)


def main():
    Console().print(
        f"[b]nyaaup[/b] [magenta bold]v{__version__}[/]\n\n[dim]Auto torrent uploader to Nyaa\n",
        justify="center",
    )

    parser = argparse.ArgumentParser(
        description="Auto torrent uploader to Nyaa", prog="nyaaup"
    )
    parser = RParse()
    subparsers = parser.add_subparsers(dest="command", required=True)
    parser_auth = subparsers.add_parser("auth")
    parser_auth.add_argument(
        "-c",
        "--credential",
        type=str,
        metavar="USER:PASS",
        default=None,
        help="Add or replace credential.",
    )
    parser_auth.add_argument(
        "-a",
        "--announces",
        type=str,
        metavar="NAME",
        default=None,
        help="Add new announces url to config.",
    )
    parser_auth.add_argument(
        "-d",
        "--domain",
        type=str,
        metavar="NAME",
        default=None,
        help="Add or replace domain.",
    )
    parser_auth.add_argument(
        "-p",
        "--provider",
        type=str,
        metavar="NAME",
        default=None,
        help="Provider name for config. (default: nyaasi)",
    )
    parser_up = subparsers.add_parser("up")
    parser_up.add_argument(
        "-ch",
        "--category-help",
        action="store_true",
        help="Print available categories.",
    )
    parser_up.add_argument(
        "-ms", "--multi-subs", action="store_true", help="Add Multi Subs tag to title."
    )
    parser_up.add_argument(
        "-t",
        "--telegram",
        action="store_true",
        help="Send telegram message.",
    )
    parser_up.add_argument(
        "-da",
        "--dual-audios",
        action="store_true",
        help="Add Dual audios tag to title.",
    )
    parser_up.add_argument(
        "-ma",
        "--multi-audios",
        action="store_true",
        help="Add Multi audios tag to title.",
    )
    parser_up.add_argument(
        "-a",
        "--auto",
        action="store_true",
        help="Detect multi subs, multi audios and dual audios.",
    )
    parser_up.add_argument(
        "-an", "--anonymous", action="store_true", help="Upload torrent as anonymous."
    )
    parser_up.add_argument(
        "-hi", "--hidden", action="store_true", help="Upload the torrent as hidden."
    )
    parser_up.add_argument(
        "-co",
        "--complete",
        action="store_true",
        help="If the torrnet is a complete batch.",
    )
    parser_up.add_argument(
        "-re",
        "--remake",
        action="store_true",
        help="If the torrnet is a remake.",
    )
    parser_up.add_argument(
        "-s", "--skip-upload", action="store_true", help="Skip torrent upload."
    )
    parser_up.add_argument(
        "-e",
        "--edit-code",
        type=str,
        default=None,
        help="Use uniq edit code for mediainfo on rentry.co",
    )
    parser_up.add_argument(
        "-i",
        "--info",
        type=str,
        default=None,
        help="Set information.",
    )
    parser_up.add_argument(
        "-p",
        "--pictures-number",
        type=int,
        default=3,
        help="Number of picture to upload to the torrent (default: 3).",
    )
    parser_up.add_argument(
        "-pe",
        "--picture-extension",
        type=str,
        default="png",
        help="Extension of the snapshot to upload (default: png).",
    )
    parser_up.add_argument(
        "-n",
        "--note",
        type=str,
        default=None,
        help="Put a note in to the description.",
    )
    parser_up.add_argument(
        "-M",
        "--no-mediainfo",
        action="store_true",
        help="Do not attach mediainfo to the torrent (provider rentry.co).",
    )
    parser_up.add_argument(
        "-m", "--myanimelist", type=str, default=None, help="MyAnimeList link."
    )
    parser_up.add_argument(
        "--skip-myanimelist",
        action="store_true",
        help="Skip anything that connect to MyAnimeList (in case of downtime).",
    )
    parser_up.add_argument(
        "-c",
        "--category",
        type=str,
        default=None,
        help="Select a category, for help use: --category-help.",
    )
    parser_up.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Recreate the .torrent if it already exists.",
    )
    parser_up.add_argument(
        "path", type=Path, nargs="*", default=None, help="File or directory to upload."
    )
    parser.set_defaults(default_command=True, command="up")
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()

    if args.command == "auth":
        Auth(args, parser)
    else:
        Upload(args, parser)


if __name__ == "__main__":
    main()
