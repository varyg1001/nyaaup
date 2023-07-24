from __future__ import annotations

import sys
import glob
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path
from typing import Optional

from rich.console import Console
import subprocess
from rich.panel import Panel
from pymediainfo import MediaInfo
from rich.tree import Tree
from rich import print
from rich.traceback import install

from .utils import (
    Config,
    creat_torrent,
    rentry_upload,
    get_description,
    get_mal_link,
    wprint,
    eprint,
    iprint,
    snapshot,
) 

install(show_locals=True)
console = Console()


class Nyaasi():

    def upload(self, torrent_byte, name: str, display_name: str, info: str, infos: Tree) -> dict:
        iprint("Uploading to Nyaa.si...", down=0)
        session = requests.Session()
        retry = Retry(connect=5, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)

        payload = {
            "torrent_data": json.dumps(
                {
                    "name": display_name,
                    "category": self.cat,
                    "information": info,
                    "description": self.description,
                    "anonymous": self.anonymous,
                    "hidden": self.hidden,
                    "complete": self.complete,
                    "trusted": None,
                }
            )
        }

        response = session.post(
            "https://nyaa.si/api/v2/upload",
            files={
                "torrent": (f'{name}.torrent', torrent_byte, "application/x-bittorrent")
            },
            data=payload,
            auth=(self.credentials[0], self.credentials[1]),
        )

        if response.json().get("errors") and "This torrent already exists" in response.json().get("errors").get("torrent")[0]:
            eprint('\nThe torrent once uploaded in the past!\n')
            print(Panel.fit(infos, border_style="red"))
            sys.exit(1)

        return response.json()

    def get_category(self, category: str) -> str:
        match category:
            case "Anime - English-translated" | "1": return "1_2"
            case "Anime - Non-English-translated" | "2": return "1_3"
            case "Anime - Raw" | "3": return "1_4"
            case "Live Action - English-Translated" | "4": return "4_1"
            case "Live Action - Non-English-translated" | "5": return "4_1"
            case "Live Action - Raw" | "6": return "4_4"
            case "1_2": return "Anime - English-translated"
            case "1_3": return "Anime - Non-English-translated"
            case "1_4": return "Anime - Raw"
            case "4_1": return "Live Action - English-Translated"
            case "4_3": return "Live Action - Non-English-translated"
            case "4_4": return "Live Action - Raw"

    def __init__(self, args, parser):

        self.args = args
        self.parser = parser

        if len(sys.argv) == 1:
            parser.print_help(sys.stderr)
            sys.exit(1)

        self.cat = self.get_category(self.args.category)
        categorys_help = Tree(
            "[chartreuse2]Available categorys:[white /not bold]")
        categorys_help.add(
            "[1] [cornflower_blue not bold]Anime - English-translated[white /not bold]")
        categorys_help.add(
            "[2] [cornflower_blue not bold]Anime - Non-English-translated[white /not bold]")
        categorys_help.add(
            "[3] [cornflower_blue not bold]Anime - Raw[white /not bold]")
        categorys_help.add(
            "[4] [cornflower_blue not bold]Live Action - English-translated[white /not bold]")
        categorys_help.add(
            "[5] [cornflower_blue not bold]Live Action - Non-English-translated[white /not bold]")
        categorys_help.add(
            "[6] [cornflower_blue not bold]Live Action - Raw[white /not bold]")

        if self.args.category_help:
            print(categorys_help)
            sys.exit(1)

        if not self.args.path:
            eprint('No input!\n')
            self.parser.print_help(sys.stdeerr)
            sys.exit(1)

        if not self.args.category:
            eprint('No selected category!\n')
            print(categorys_help)
            sys.exit(1)

        self.pic_num = self.args.pictures_number

        self.hidden = 'hidden' if self.args.hidden else None
        self.anonymous = 'anonymous' if self.args.anonymous else None
        self.complete = 'complete' if self.args.complete else None

        self.main()

    def main(self):
        dirs = Config().get_dirs()
        Path(dirs.user_config_path).mkdir(parents=True, exist_ok=True)
        self.config = Config().load()

        self.edit_code: Optional[str] = self.config["preferences"]["edit_code"] if not self.args.edit_code else self.args.edit_code

        self.credentials: Optional[dict] = Config.get_cred(self.config["credentials"])

        try:
            info_form_config: bool = False if self.config["preferences"]["info"].lower() == "mal" else True
        except AttributeError:
            info_form_config: bool = False

        add_mal: bool = self.config["preferences"]["mal"]
        mediainfo_to_torrent: bool = self.config["preferences"]["mediainfo"] if not self.args.no_mediainfo else False

        multi_sub: bool = self.args.multi_subs
        multi_audio: bool = self.args.multi_audios
        dual_audio: bool = self.args.dual_audios

        for in_file in self.args.path:

            self.description: str = ""
            if note := self.args.note:
                self.description += f"{note}\n\n---\n\n"
            name_plus = list()

            if not in_file.exists():
                eprint("Input file doens't exist!", True)

            if in_file.is_file():
                file = in_file
                name = str(in_file.name).removesuffix('.mkv').removesuffix('.mp4')
            else:
                file = Path(
                    sorted([*in_file.glob("*.mkv"), *in_file.glob("*.mp4")])[0])
                name = in_file.name

            self.cache_dir = dirs.user_cache_path / f"{name}_files"
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            if not self.args.skip_upload:
                creat_torrent(self, name, in_file)
                torrent_fd = open(f'{self.cache_dir}/{name}.torrent', "rb")
            else:
                wprint("No torrent file created!")

            with console.status("[bold magenta]MediaInfo parseing...") as status:
                mediainfo = json.loads(subprocess.run(
                    ["mediainfo",  "--ParseSpeed=1.0", "-f", "--output=JSON", file], capture_output=True, encoding="utf-8").stdout)["media"]["track"]

                self.text = MediaInfo.parse(file, output="", full=False).replace(str(file), str(file.name))

            if self.cat in {"1_2", "1_3", "1_4"}:
                anime = True
            else: anime = False

            if anime and add_mal and not info_form_config and not self.args.skip_myanimelist:
                mal_data, name_to_mal = get_mal_link(anime, self.args.myanimelist, name)

            information: Optional[str] = None

            if add_mal and not self.args.skip_myanimelist:
                if not info_form_config and anime:
                    if self.args.myanimelist:
                        information = self.args.myanimelist
                    else:
                        information = f"{'/'.join(mal_data.url.split('/')[:-1])}/"
                elif info_form_config:
                    information = self.config["preferences"]["info"]

            videode, audiode, subde = get_description(mediainfo)
            self.description += f'Informations:\n* Video: {videode}\n* Audio(s): {" │ ".join(audiode)}\n* Subtitle(s): {" │ ".join(subde)}\n* Duration: **~{mediainfo[0].get("Duration_String4")}**'

            if not self.args.skip_upload and mediainfo_to_torrent:
                try:
                    rentry_response = rentry_upload(self)
                    mediainfo_url = rentry_response['url']
                    edit_code = rentry_response['edit_code']
                    self.description += f"\n\n[MediaInfo]({mediainfo_url}/raw)"
                except requests.HTTPError as e:
                    wprint(f"Failed to upload mediainfo to rentry.co! ({e.response})")
            self.description += "\n\n---\n\n"

            sublen: int = len(set(subde))
            audiodelen: int = len(set(audiode))

            if self.args.auto:
                if audiodelen == 2:
                    dual_audio = True
                elif audiodelen > 2:
                    multi_audio = True
                if sublen > 1:
                    multi_sub = True

            name = name.replace(".", " ").replace("2 0", "2.0").replace("5 1", "5.1").replace("7 1", "7.1")

            if add_mal and anime and not self.args.skip_myanimelist:
                if self.cat in {"1_3", "1_4"}:
                    if mal_data.title_english and mal_data.title_english.casefold() not in name_to_mal.casefold():
                        name_plus.append(mal_data.title_english)
                else:
                    if mal_data.title.casefold() not in name_to_mal.casefold():
                        name_plus.append(mal_data.title)

            if dual_audio:
                name_plus.append('Dual-audio')
            elif multi_audio:
                name_plus.append('Multi-Audios')
            if multi_sub:
                name_plus.append('Multi-Subs')

            display_name = f'{name} ({", ".join(name_plus)})' if name_plus else name

            if self.pic_num != 0 and not self.args.skip_upload:
                images: Tree = snapshot(self, file, name, mediainfo)

            infos = Tree("[bold white]Informations[not bold]")
            if add_mal and anime and info_form_config:
                infos.add(f"[bold white]MAL link ({name_to_mal}): [cornflower_blue not bold]{information}[white]")
            infos.add(f"[bold white]Selected category: [cornflower_blue not bold]{self.get_category(self.cat)}[white]")

            title: str = ""
            style: str = "yellow"

            if not self.args.skip_upload:
                if mediainfo_to_torrent:
                    medlink = Tree(f"[bold white]Mediainfo link: [cornflower_blue not bold]{mediainfo_url}[white]")
                    medlink.add(f"[bold white]Edit code: [cornflower_blue not bold]{edit_code}[white]")
                    infos.add(medlink)
                if self.pic_num != 0:
                    infos.add(images)
                link = self.upload(torrent_fd, name, display_name, information, infos)
                if not link:
                    wprint("Something happened during the uploading!", True)
                else:
                    infos.add(f'[bold white]Page link: [cornflower_blue not bold]{link["url"]}[white]')
                    infos.add(f'[bold white]Download link:[cornflower_blue not bold] https://nyaa.si/download/{link["id"]}.torrent[white]')
                    style = "bold green"
                    title = "Torrent successfuly uploaded!"
            else:
                wprint("Torrent is not uploaded!")
            print('')
            print(Panel.fit(infos, title=title, border_style=style))
