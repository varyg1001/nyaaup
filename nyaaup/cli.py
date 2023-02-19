#!/usr/bin/env python3

from .nyaaup import Nyaasi
from .auth import Auth

import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Auto torrent uploader to Nyaa.si', prog='nyaaup')
    subparsers =  parser.add_subparsers(dest="command")
    parser_auth = subparsers.add_parser("auth")
    parser_up = subparsers.add_parser("up")
    parser_auth.add_argument('-add', '--add-credential',
                        type=str,
                        default=None,
                        help="Add or replace credential in config file. (format: user:pass)")
    parser_up.add_argument('-ch', '--category-help',
                        action='store_true',
                        help='Print available categories.')
    parser_up.add_argument('-ms', '--multi-subs',
                        action='store_true',
                        help='Add Multi-Subs tag to title.')
    parser_up.add_argument('-da', '--dual-audios',
                        action='store_true',
                        help='Add Dual-audios tag to title.')
    parser_up.add_argument('-ma', '--multi-audios',
                        action='store_true',
                        help='Add Multi-audios tag to title.')
    parser_up.add_argument('-A', '--auto',
                        action='store_true',
                        help='Detect multi-subs, multi-audios and dual-audios (if sub or audio more than one it will add the tags)')
    parser_up.add_argument('-a', '--anonymous',
                        action='store_true',
                        help='Upload torrent as anonymous.')
    parser_up.add_argument('-H', '--hidden',
                        action='store_true',
                        help='Upload the torrent as hidden.')
    parser_up.add_argument('-C', '--complete',
                        action='store_true',
                        help='If the torrnet is a complete batch.')
    parser_up.add_argument('-s', '--skip-upload',
                        action='store_true',
                        help='Skip torrent upload.')
    parser_up.add_argument('-e', '--edit-code',
                        type=str,
                        default=None,
                        help='Use uniq edit code for mediainfo on rentry.co')
    parser_up.add_argument('-p', '--pictures-number',
                        type=int,
                        default=3,
                        help='Number of picture to upload to the torrent (default: 3).'),
    parser_up.add_argument('-mal', '--myanimelist',
                        type=str,
                        default=None,
                        help='MyAnimeList link.') 
    parser_up.add_argument('-c', '--category',
                        type=str,
                        choices=['1', 'Anime - English-translated', '2', 'Anime - Non-English-translated', '3', 'Anime - Raw', '4', 'Live Action - English-translated', '5', 'Live Action - Raw', '6', 'Live Action - Non-English-translate'],
                        default=None,
                        help='Select a category to upload the torrent.')
    parser_up.add_argument("path",
                        type=Path,
                        nargs="*",
                        default=None,
                        help="File or directory to upload.")
    parser.set_defaults(default_command=True, command='up')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.command == "auth":
        Auth(args, parser)
    else:
        Nyaasi(args, parser)

if __name__ == "__main__":
    main()