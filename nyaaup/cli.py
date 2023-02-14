#!/usr/bin/env python3

from .nyaaup import Nyaasi

import argparse
import sys
from json import loads

from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Nyaa.si auto torrent uploader.', prog='nyaaup')
    parser.add_argument('-ch', '--category-help',
                        action='store_true',
                        help='Print available categories.')
    parser.add_argument('-ms', '--multi-subs',
                        action='store_true',
                        help='Add Multi-Subs tag to title.')
    parser.add_argument('-da', '--dual-audios',
                        action='store_true',
                        help='Add Dual-audios tag to title.')
    parser.add_argument('-ma', '--multi-audios',
                        action='store_true',
                        help='Add Multi-audios tag to title.')
    parser.add_argument('-A', '--auto',
                        action='store_true',
                        help='Detect multi-subs, multi-audios and dual-audios (if sub or audio more than one it will add the tags)')
    parser.add_argument('-a', '--anonymous',
                        action='store_true',
                        help='Upload torrent as anonymous.')
    parser.add_argument('-H', '--hidden',
                        action='store_true',
                        help='Upload the torrent as hidden.')
    parser.add_argument('-C', '--complete',
                        action='store_true',
                        help='If the torrnet is a complete batch.')
    parser.add_argument('-s', '--skip-upload',
                        action='store_true',
                        help='Skip torrent upload.')
    parser.add_argument('-e', '--edit-code',
                        type=str,
                        default=None,
                        help='Use uniq edit code for mediainfo on rentry.co')
    parser.add_argument('-p', '--pictures-number',
                        type=int,
                        default=3,
                        help='Number of picture to upload to the torrent (default: 3).'),
    parser.add_argument('-mal', '--myanimelist',
                        type=str,
                        default=None,
                        help='MyAnimeList link.') 
    parser.add_argument('-c', '--category',
                        type=str,
                        choices=['1', 'Anime - English-translated', '2', 'Anime - Non-English-translated', '3', 'Anime - Raw', '4', 'Live Action - English-translated', '5', 'Live Action - Raw', '6', 'Live Action - Non-English-translate'],
                        default=None,
                        help='Select a category to upload the torrent.')
    parser.add_argument("path",
                        type=Path,
                        nargs="*",
                        default=None,
                        help="File or directory to upload.")
    parser.add_argument('-add', '--add-credential',
                        type=str,
                        default=None,
                        help="Add or replace credential in config file.")
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    Nyaasi(args, parser)

if __name__ == "__main__":
    main()