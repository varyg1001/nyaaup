import sys
import json
from pathlib import Path
from typing import Any, Optional

import httpx
from mal import Anime
from rich.console import Console
from rich.panel import Panel
from pymediainfo import MediaInfo
from rich.tree import Tree
from rich import print
from rich.traceback import install

from .utils import (
    Config,
    create_torrent,
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


class Nyaasi:
    def __init__(self, args, parser):
        self.args = args
        self.parser = parser

        if len(sys.argv) == 1:
            parser.print_help(sys.stderr)
            sys.exit(1)

        self.category = self.get_category(self.args.category)
        categories_help = Tree("[chartreuse2]Available categories:[white /not bold]")
        categories_help.add(
            "[1] [cornflower_blue not bold]Anime - English-translated[white /not bold]"
        )
        categories_help.add(
            "[2] [cornflower_blue not bold]Anime - Non-English-translated[white /not bold]"
        )
        categories_help.add(
            "[3] [cornflower_blue not bold]Anime - Raw[white /not bold]"
        )
        categories_help.add(
            "[4] [cornflower_blue not bold]Live Action - English-translated[white /not bold]"
        )
        categories_help.add(
            "[5] [cornflower_blue not bold]Live Action - Non-English-translated[white /not bold]"
        )
        categories_help.add(
            "[6] [cornflower_blue not bold]Live Action - Raw[white /not bold]"
        )

        if self.args.category_help:
            print(categories_help)
            sys.exit(1)

        if not self.args.path:
            eprint("No input!\n")
            self.parser.print_help(sys.stderr)
            sys.exit(1)

        if not self.args.category:
            eprint("No selected category!\n")
            print(categories_help)
            sys.exit(1)

        self.pic_ext = self.args.picture_extension
        self.pic_num = self.args.pictures_number

        self.hidden = "hidden" if self.args.hidden else None
        self.anonymous = "anonymous" if self.args.anonymous else None
        self.complete = "complete" if self.args.complete else None

        self.main()

    def upload(
        self, torrent_byte: Any, name: str, display_name: str, info: str, infos: Tree
    ) -> dict:
        iprint("Uploading to Nyaa...", down=0)

        with httpx.Client(transport=httpx.HTTPTransport(retries=2)) as client:
            res = client.post(
                url=self.up_api,
                files={
                    "torrent": (
                        f"{name}.torrent",
                        torrent_byte,
                        "application/x-bittorrent",
                    )
                },
                data={
                    "torrent_data": json.dumps(
                        {
                            "name": display_name,
                            "category": self.category,
                            "information": info,
                            "description": self.description,
                            "anonymous": self.anonymous,
                            "hidden": self.hidden,
                            "complete": self.complete,
                            "trusted": self.trusted,
                        }
                    )
                },
                auth=(self.credentials[0], self.credentials[1]),
                headers=self.headers,
            )

        if (
            res.json().get("errors")
            and "This torrent already exists"
            in res.json().get("errors").get("torrent")[0]
        ):
            eprint("\nThe torrent once uploaded in the past!\n")
            print(Panel.fit(infos, border_style="red"))
            sys.exit(1)

        return res.json()

    def get_category(self, category: str) -> Optional[str]:
        match category:
            case "Anime - English-translated" | "1":
                return "1_2"
            case "Anime - Non-English-translated" | "2":
                return "1_3"
            case "Anime - Raw" | "3":
                return "1_4"
            case "Live Action - English-Translated" | "4":
                return "4_1"
            case "Live Action - Non-English-translated" | "5":
                return "4_1"
            case "Live Action - Raw" | "6":
                return "4_4"
            case "1_2":
                return "Anime - English-translated"
            case "1_3":
                return "Anime - Non-English-translated"
            case "1_4":
                return "Anime - Raw"
            case "4_1":
                return "Live Action - English-Translated"
            case "4_3":
                return "Live Action - Non-English-translated"
            case "4_4":
                return "Live Action - Raw"

    def main(self) -> None:
        config = Config()
        dirs = config.get_dirs()
        Path(dirs.user_config_path).mkdir(parents=True, exist_ok=True)
        self.config = config.load() or {}
        if pref := self.config.get("preferences"):
            self.edit_code: Optional[str] = (
                pref.get("edit_code")
                if not self.args.edit_code
                else self.args.edit_code
            )
            self.up_api: str = self.config.get(
                "up_api", "https://nyaa.si/api/v2/upload"
            )
            self.random_snapshots: str = pref.get("random_snapshots", False)
            self.real_lenght: bool = not pref.get("real_lenght", False)
            if cred := self.config.get("credentials"):
                self.credentials: dict = config.get_cred(cred)
            else: 
                eprint("No credentials in the config!", True)
            self.trusted = "trusted" if self.config.get("trusted", False) else None
            info_form_config: bool = (
                False
                if (pref.get("info", "").lower() == "mal") or not pref.get("info")
                else True
            )
            self.headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.46",
                    "sec-ch-ua": '"Chromium";v="118", "Microsoft Edge";v="118", "Not=A?Brand";v="99"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                }
            self.kek_headers = {}
            if key := pref.get("keks_key", None):
                self.kek_headers["x-kek-auth"] = key
                self.kek_headers.update(self.headers)

            add_mal: bool = pref.get("mal", True)
            mediainfo_to_torrent: bool = (
                pref.get("mediainfo", True) if not self.args.no_mediainfo else False
            )
            self.add_pub_trackers: bool = pref.get("add_pub_trackers", False)
        else:
            eprint("No preferences in the config!", True)

        multi_sub: bool = self.args.multi_subs
        multi_audio: bool = self.args.multi_audios
        dual_audio: bool = self.args.dual_audios

        for in_file in self.args.path:
            self.in_f = in_file
            self.description: str = ""
            if note := self.args.note:
                self.description += f"{note}\n\n---\n\n"
            name_plus = list()

            if not in_file.exists():
                eprint("Input file doesn't exist!", True)

            if in_file.is_file():
                file = in_file
                name = str(in_file.name).removesuffix(".mkv").removesuffix(".mp4")
            else:
                file = Path(sorted([*in_file.glob("*.mkv"), *in_file.glob("*.mp4")])[0])
                name = in_file.name

            self.cache_dir = dirs.user_cache_path / f"{name}_files"
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            create_torrent(self, name, in_file, self.args.overwrite)

            with console.status("[bold magenta]MediaInfo parsing...") as _:
                mediainfo = json.loads(MediaInfo.parse(file, output="JSON", full=True))[
                    "media"
                ]["track"]

                reparse_main = False
                if not mediainfo[0]["Duration"]:
                    reparse_main = True
                else:
                    for m in mediainfo:
                        if m.get("@type", "") in ["Video", "Audio"] and not m.get(
                            "BitRate"
                        ):
                            reparse_main = True
                        if m.get("@type", "") == "General" and not m.get("Duration"):
                            reparse_main = True

                if reparse_main:
                    mediainfo: dict = json.loads(
                        MediaInfo.parse(file, output="JSON", parse_speed=1, full=True)
                    )["media"]["track"]

                self.text = MediaInfo.parse(
                    file, output="", parse_speed=1 if reparse_main else 0.5, full=False
                ).replace(str(file), str(file.name))

            if self.category in {"1_2", "1_3", "1_4"}:
                anime = True
            else:
                anime = False

            name_to_mal: str = ""
            mal_data: Optional[Anime] = None

            if (
                anime
                and add_mal
                and not info_form_config
                and not self.args.skip_myanimelist
            ):
                mal_data, name_to_mal = get_mal_link(self.args.myanimelist, name)

            information: str = ""
            if not info_form_config and anime and not self.args.info:
                if add_mal and not self.args.skip_myanimelist:
                    if self.args.myanimelist:
                        information = self.args.myanimelist
                    else:
                        information = f"{'/'.join(mal_data.url.split('/')[:-1])}/"
            elif self.args.info or info_form_config:
                information = self.args.info or pref["info"]

            videode, audiode, subde = get_description(mediainfo)

            sublen: int = (
                len(set([x.split("**")[1] for x in subde]))
                if len(subde) > 1
                else len(subde)
            )
            audiodelen: int = (
                len(set([x.split("**")[1] for x in audiode]))
                if len(audiode) > 1
                else len(audiode)
            )

            self.description += f'`Tech Specs:`\n* `Video:` {videode}\n* `Audios ({audiodelen if self.real_lenght else len(audiode)}):` {" │ ".join(audiode)}\n* `Subtitles ({sublen if self.real_lenght else len(subde)}):` {" │ ".join(subde)}\n* `Chapters:` **{"Yes" if mediainfo[0].get("MenuCount") else "No"}**\n* `Duration:` **~{mediainfo[0].get("Duration_String3")}**'

            mediainfo_url = ""
            edit_code = ""
            if not self.args.skip_upload and mediainfo_to_torrent:
                try:
                    rentry_response = rentry_upload(self)
                    mediainfo_url = rentry_response["url"]
                    edit_code = rentry_response["edit_code"]
                    self.description += f"\n\n[MediaInfo]({mediainfo_url}/raw)"
                except httpx.HTTPError as e:
                    wprint(f"Failed to upload mediainfo to rentry.co! ({e})")
            self.description += "\n\n---\n\n"

            if self.args.auto:
                if audiodelen == 2:
                    dual_audio = True
                elif audiodelen > 2:
                    multi_audio = True
                if sublen > 1:
                    multi_sub = True

            name_nyaa = (
                name.replace(".", " ")
                .replace("2 0", "2.0")
                .replace("5 1", "5.1")
                .replace("7 1", "7.1")
            )

            if mal_data and add_mal and anime and not self.args.skip_myanimelist:
                if self.category in {"1_3", "1_4"}:
                    if (
                        mal_data.title_english
                        and mal_data.title_english.casefold()
                        not in name_to_mal.casefold()
                    ):
                        name_plus.append(mal_data.title_english)
                else:
                    if mal_data.title.casefold() not in name_to_mal.casefold():
                        name_plus.append(mal_data.title)

            if dual_audio:
                name_plus.append("Dual-Audio")
            elif multi_audio:
                name_plus.append("Multi-Audio")
            if multi_sub:
                name_plus.append("Multi-Subs")

            display_name = f'{name_nyaa} ({", ".join(name_plus)})' if name_plus else name_nyaa

            images: Optional[Tree] = None
            if self.pic_num != 0:
                images = snapshot(self, file, name_nyaa, mediainfo)

            infos = Tree("[bold white]Information[not bold]")
            if add_mal and anime and info_form_config and name_to_mal:
                infos.add(
                    f"[bold white]MAL link ({name_to_mal}): [cornflower_blue not bold]{information}[white]"
                )
            if self.category:
                infos.add(
                    f"[bold white]Selected category: [cornflower_blue not bold]{self.get_category(self.category)}[white]"
                )

            title: str = ""
            style: str = "yellow"

            if not self.args.skip_upload:
                if mediainfo_to_torrent and mediainfo_url and edit_code:
                    medlink = Tree(
                        f"[bold white]MediaInfo link: [cornflower_blue not bold][link={mediainfo_url}]{mediainfo_url}[/link][white]"
                    )
                    medlink.add(
                        f"[bold white]Edit code: [cornflower_blue not bold]{edit_code}[white]"
                    )
                    infos.add(medlink)
                if self.pic_num != 0:
                    infos.add(images)
                torrent_fd: Any = open(f"{self.cache_dir}/{name}.torrent", "rb")
                link = self.upload(torrent_fd, name_nyaa, display_name, information, infos)
                if not link:
                    wprint("Something happened during the uploading!")
                else:
                    infos.add(
                        f'[bold white]Page link: [cornflower_blue not bold][link={link["url"]}]{link["url"]}[/link][white]'
                    )
                    infos.add(
                        f"""[bold white]Download link: [cornflower_blue not bold]{link["url"].replace(f"view/{link['id']}", f"download/{link['id']}.torrent")}[white]"""
                    )
                    style = "bold green"
                    title = "Torrent successfully uploaded!"
            else:
                wprint("Torrent is not uploaded!")
            print("")
            print(Panel.fit(infos, title=title, border_style=style))
