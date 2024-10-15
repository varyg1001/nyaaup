import re
import sys
import json
import time
from pathlib import Path
from typing import Any, Optional
from types import SimpleNamespace

import httpx
from mal import Anime
from rich.console import Console
from rich.panel import Panel
from pymediainfo import MediaInfo
from rich.tree import Tree
from rich import print
from rich.traceback import install

from .utils import (
    create_torrent,
    rentry_upload,
    get_description,
    get_mal_link,
    wprint,
    eprint,
    iprint,
    snapshot,
    tgpost,
    cat_help,
    Config,
)

install(show_locals=True)


class Upload:
    def __init__(self, args, parser):
        self.args = args
        self.parser = parser

        if len(sys.argv) == 1:
            parser.print_help(sys.stderr)
            sys.exit(1)

        self.category = self.get_category(self.args.category)

        if self.args.category_help:
            cat_help()
            sys.exit(1)

        if not self.args.path:
            eprint("No input!\n")
            self.parser.print_help(sys.stderr)
            sys.exit(1)

        if not self.args.category:
            eprint("No selected category!\n")
            cat_help()
            sys.exit(1)

        self.pic_ext = self.args.picture_extension
        self.pic_num = self.args.pictures_number

        self.hidden = "hidden" if self.args.hidden else None
        self.anonymous = "anonymous" if self.args.anonymous else None
        self.complete = "complete" if self.args.complete else None
        self.remake = "remake" if self.args.remake else None

        self.main()

    def edit(self, cookies, provider, id, display_name, information) -> bool:
        with httpx.Client(transport=httpx.HTTPTransport(retries=2)) as client:
            res = client.post(
                url=f"{provider.domain}/view/{id}/edit",
                files={
                    "display_name": (
                        None,
                        display_name,
                    ),
                    **({"is_anonymous": (None, "y")} if self.anonymous else {}),
                    **({"is_remake": (None, "y")} if self.remake else {}),
                    **({"is_complete": (None, "y")} if self.complete else {}),
                    **({"is_hidden": (None, "y")} if self.hidden else {}),
                    "category": (None, self.category),
                    "information": (None, information),
                    "description": (
                        None,
                        self.description,
                    ),
                    "submit": (None, "Save Changes"),
                },
                cookies=cookies,
                headers={
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "content-type": "multipart/form-data; boundary=----WebKitFormBoundary",
                    "origin": provider.domain,
                    "referer": f"{provider.domain}/view/{id}/edit",
                    **self.headers,
                },
            )

            if res.status_code != 302:
                eprint("Failed to add iamges the the torrent!")
                return False

            return True

    def upload(
        self,
        torrent_byte: Any,
        name: str,
        display_name: str,
        info: str,
        infos: Tree,
        provider,
        cookies,
    ) -> dict:
        iprint(
            "Uploading to Nyaa...",
            down=0 if not cookies else 1,
            up=1 if not cookies else 0,
        )

        with httpx.Client(transport=httpx.HTTPTransport(retries=5)) as client:
            res = client.post(
                url=provider.domain + "/api/v2/upload",
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
                            "remake": self.remake,
                            "trusted": self.trusted,
                        }
                    )
                },
                auth=(provider.credentials.username, provider.credentials.password),
                headers=self.headers,
            )

        try:
            res = res.json()
        except json.JSONDecodeError:
            eprint(f"Failed to decode JSON: {res.text}", True)

        if error := res.get("errors"):
            if isinstance(error, str):
                eprint(f"\n{error}!\n")
            else:
                info = next(iter(error))
                eprint(f"\n{info} error: {error[info][0]}!\n")
            print(Panel.fit(infos, border_style="red"))
            sys.exit(1)

        return res

    def get_category(self, category: str) -> Optional[str]:
        match category:
            case "Anime - Anime Music Video" | "7":
                return "1_1"
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
            case "1_1":
                return "Anime - Anime Music Video"
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
        dirs = config.get_dirs
        Path(dirs.user_config_path).mkdir(parents=True, exist_ok=True)
        self.config = config.load() or {}
        if pref := self.config.get("preferences"):
            self.edit_code: Optional[str] = (
                pref.get("edit_code")
                if not self.args.edit_code
                else self.args.edit_code
            )

            self.random_snapshots: str = pref.get("random_snapshots", False)
            self.real_lenght: bool = not pref.get("real_lenght", False)
            self.tg_id: Optional[str] = pref.get("id", None)
            self.note: Optional[str] = pref.get("note", None)
            self.telegram: bool = pref.get("telegram", False)
            self.tg_token = pref.get("token", None)
            self.announces = []
            self.providers = []
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

        if providers := self.config.get("providers"):
            for x in providers:
                temp = {}
                temp["name"] = ""
                if name := x.get("name"):
                    temp["name"] = name
                if cred := x.get("credentials"):
                    temp["credentials"] = config.get_cred(cred)
                else:
                    eprint("No credentials in the config!", True)
                if domain := x.get("domain"):
                    temp["domain"] = domain
                else:
                    eprint("No domain in the config!", True)
                if announces := x.get("announces"):
                    self.announces.extend(announces)
                else:
                    wprint("No announces in the config!")
                self.providers.append(SimpleNamespace(**temp))
        else:
            eprint("No providers in the config!", True)

        multi_sub: bool = self.args.multi_subs
        multi_audio: bool = self.args.multi_audios
        dual_audio: bool = self.args.dual_audios

        for in_file in self.args.path:
            self.in_f = in_file
            self.description: str = ""
            if note := (self.args.note or self.note):
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

            with Console().status("[bold magenta]MediaInfo parsing...") as _:
                mediainfo = json.loads(MediaInfo.parse(file, output="JSON", full=True))[
                    "media"
                ]["track"]

                reparse_main = False
                if not mediainfo[0]["Duration"]:
                    reparse_main = True
                else:
                    for m in mediainfo:
                        if m.get("@type", "") in ("Audio") and not m.get("BitRate"):
                            reparse_main = True
                        if m.get("@type", "") == "General" and not m.get("Duration"):
                            reparse_main = True

                if reparse_main:
                    mediainfo = json.loads(
                        MediaInfo.parse(file, output="JSON", parse_speed=1, full=True)
                    )["media"]["track"]

                self.text: str = MediaInfo.parse(
                    file, output="", parse_speed=1 if reparse_main else 0.5, full=False
                ).replace(str(file), str(file.name))

            if self.category in {"1_2", "1_3", "1_4"}:
                anime = True
            else:
                anime = False

            mal_data: Optional[Anime] = None

            if (
                anime
                and add_mal
                and not info_form_config
                and not self.args.skip_myanimelist
            ):
                name_to_mal = re.sub(r"[\.|\-]S\d+.*", "", name)
                if name_to_mal == name:
                    name_to_mal = re.sub(r"[\.|\-]\d{4}\..*", "", name)
                name_to_mal = name_to_mal.replace(".", " ")
                mal_data = get_mal_link(self.args.myanimelist, name_to_mal)

            information: str = ""
            if not info_form_config and anime and not self.args.info:
                if add_mal and not self.args.skip_myanimelist:
                    if self.args.myanimelist:
                        information = self.args.myanimelist
                    elif mal_data and getattr(mal_data, "url", None):
                        information = f"{'/'.join(mal_data.url.split('/')[:-1])}/"
            elif self.args.info or info_form_config:
                information = self.args.info or pref["info"]

            video_de, audio_de, sub_de = get_description(mediainfo)

            audiode_str: str = " │ ".join(audio_de)
            subde_str: str = " │ ".join(sub_de)
            if not subde_str:
                subde_str = "**N/A**"
            chapter_str: str = ["No", "Yes"][bool(mediainfo[0].get("MenuCount", False))]
            duration_str: str = mediainfo[0].get("Duration_String3", "?")

            sub_len: int = len(sub_de)
            audio_len: int = len(audio_de)
            if self.real_lenght:
                if sub_len > 1:
                    sub_len = len(set([x.split("**")[1] for x in sub_de]))
                if audio_len > 1:
                    audio_len = len(set([x.split("**")[1] for x in audio_de]))

            self.description += (
                f"`Tech Specs:`\n* `Video:` {video_de}"
                + f"\n* `Audios ({audio_len}):` {audiode_str}"
                + f"\n* `Subtitles ({sub_len}):` {subde_str}"
                + f"\n* `Chapters:` **{chapter_str}**"
                + f"\n* `Duration:` **~{duration_str}**"
            )

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
                if audio_len == 2:
                    dual_audio = True
                elif audio_len > 2:
                    multi_audio = True
                if sub_len > 1:
                    multi_sub = True

            name_nyaa = name.replace(".", " ")
            if channel := re.search(r"[A-Z]{3}[2|5|7] [0|1]", name_nyaa):
                c = channel[0]
                name_nyaa = name_nyaa.replace(c, c.replace(" ", "."))

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

            display_name = (
                f'{name_nyaa} ({", ".join(name_plus)})' if name_plus else name_nyaa
            )
            images: Optional[Tree] = None
            if not config.cookies and self.pic_num != 0:
                images = snapshot(self, file, name_nyaa, mediainfo)

            for provider in self.providers:
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

                    if images and self.pic_num != 0:
                        infos.add(images)

                    torrent_fd: Any = open(f"{self.cache_dir}/{name}.torrent", "rb")
                    link = self.upload(
                        torrent_fd,
                        name_nyaa,
                        display_name,
                        information,
                        infos,
                        provider,
                        config.cookies,
                    )

                    if not link:
                        wprint("Something happened during the uploading!")
                    else:
                        page_link = link["url"]
                        infos.add(
                            f"[bold white]Page link: [cornflower_blue not bold][link={page_link}]{page_link}[/link][white]"
                        )
                        download_link = page_link.replace(
                            f"view/{link['id']}", f"download/{link['id']}.torrent"
                        )
                        infos.add(
                            f"""[bold white]Download link: [cornflower_blue not bold]{download_link}[white]"""
                        )
                        style = "bold green"
                        title = f"Torrent successfully uploaded to {provider.name}!"

                        try:
                            # Skip images if could not edit the upload.
                            if config.cookies:
                                if self.pic_num != 0:
                                    images = snapshot(self, file, name_nyaa, mediainfo)
                                if images and self.pic_num != 0:
                                    infos.add(images)

                                for num in range(5):
                                    is_images_up = self.edit(
                                        config.cookies,
                                        provider,
                                        link["id"],
                                        display_name,
                                        information,
                                    )
                                    if is_images_up:
                                        break
                                    else:
                                        time.sleep(5 * num)
                        except Exception as e:
                            wprint(f"Failed to add images to the torrent! ({e})")
                            style = "yellow"
                            title = f"Torrent successfully uploaded to {provider.name}, but could not add images!"

                        if (
                            (self.args.telegram or self.telegram)
                            and self.tg_id
                            and self.tg_token
                        ):
                            tgpost(
                                self,
                                ms=f'\n{display_name}\n\nNyaa link: {page_link}\n\n<a href="{download_link}">Torrent file</a>',
                            )
                else:
                    wprint("Torrent is not uploaded!")
                print("")
                print(Panel.fit(infos, title=title, border_style=style))
