import argparse
import asyncio
import aiofiles
import random
import subprocess
import humanize
import sys
import re
import os
import shutil
from tls_client import Session
from pathlib import Path
from typing import Any, IO, Literal, NoReturn, overload, Optional
from types import SimpleNamespace

import httpx
import oxipng
from httpx._client import AsyncClient
from difflib import SequenceMatcher
from torf import Torrent
from wand.image import Image
from langcodes import Language
from mal import AnimeSearch, Anime
from ruamel.yaml import YAML
from platformdirs import PlatformDirs
from rich.tree import Tree
from rich.text import Text
from rich.padding import Padding
from rich.console import Console
from rich import print as rprint
from rich.panel import Panel
from rich.progress import (
    Task,
    Progress,
    BarColumn,
    TextColumn,
    ProgressColumn,
    TaskProgressColumn,
    MofNCompleteColumn,
    TimeRemainingColumn,
)

dirs = PlatformDirs(appname="nyaaup", appauthor=False)
transport = httpx.HTTPTransport(retries=5)
console = Console()

SUB_CODEC_MAP = {"UTF-8": "SRT"}
AUDIO_CODEC_MAP = {
    "E-AC-3": "DDP",
    "AC-3": "DD",
    "fLaC": "FLAC",
}
CHANNEL_MAP = {
    "1": "1.0",
    "2": "2.0",
    "6": "5.1",
    "8": "7.1",
}


class CustomTransferSpeedColumn(ProgressColumn):
    def render(self, task: Task) -> Text:
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("--", style="progress.data.speed")
        data_speed = humanize.naturalsize(int(speed), binary=True)
        return Text(f"{data_speed}/s", style="progress.data.speed")


def lprint(
    text: Any = "",
    highlight: bool = False,
    file: IO[str] = sys.stdout,
    flush: bool = False,
    **kwargs: Any,
) -> None:
    with Console(highlight=highlight) as cons:
        cons.print(text, **kwargs)
        if flush:
            file.flush()


@overload
def eprint(text: str, fatal: Literal[False] = False, exit_code: int = 1) -> None:
    ...


@overload
def eprint(text: str, fatal: Literal[True], exit_code: int = 1) -> NoReturn:
    ...


def eprint(text: str, fatal: bool = False, exit_code: int = 1) -> None | NoReturn:
    if text.startswith("\n"):
        text = text.lstrip("\n")
        lprint()
    lprint(f"[bold color(231) on red]ERROR:[/] [red]{text}[/]")
    if fatal:
        sys.exit(exit_code)
    return None


def iprint(text: str, up: int = 1, down: int = 1) -> None:
    lprint(Padding(f"[bold green]{text}[white]", (up, 0, down, 0), expand=False))


def wprint(text: str) -> None:
    if text.startswith("\n"):
        text = text.lstrip("\n")
        lprint()
    lprint(f"[bold color(231) on yellow]WARNING:[/] [yellow]{text}[/]")


def snapshot(self, input: Path, name: str, mediainfo: list) -> Tree:
    async def up(image_path: Path, upload, progress) -> str:
        async with aiofiles.open(image_path, "rb") as file:
            content = await file.read()
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    url="https://kek.sh/api/v1/posts",
                    headers=self.kek_headers,
                    files={"file": content},
                )

                res = res.json()
                progress.update(upload, advance=1)
                return f'https://i.kek.sh/{res["filename"]}'

    async def upload_files(files, upload, progress):
        upload_tasks = [up(file, upload, progress) for file in files]
        uploaded_links = await asyncio.gather(*upload_tasks)

        return uploaded_links

    images = Tree("[bold white]Images[not bold]")
    num_snapshots = self.pic_num + 1
    snapshots: list[Path] = []
    with Progress(
        TextColumn("[progress.description]{task.description}[/]"),
        "•",
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TextColumn("Time:"),
        TimeRemainingColumn(elapsed_when_finished=True, compact=True),
    ) as progress:
        generate = progress.add_task(
            "[bold magenta]Generating snapshots[not bold white]", total=self.pic_num
        )

        for x in range(1, num_snapshots):
            snap = Path(f"{self.cache_dir}/{name}_{x}.{self.pic_ext}")
            if not snap.exists():
                duration = float(mediainfo[0].get("Duration"))
                interval = duration / (num_snapshots + 1)
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-v",
                        "error",
                        "-ss",
                        str(
                            random.randint(
                                round(interval * 10),
                                round(interval * 10 * num_snapshots),
                            )
                            / 10
                            if self.random_snapshots
                            else str(interval * (x + 1))
                        ),
                        "-i",
                        input,
                        "-vf",
                        "scale='max(sar,1)*iw':'max(1/sar,1)*ih'",
                        "-frames:v",
                        "1",
                        str(snap),
                    ],
                    check=True,
                )

                with Image(filename=snap) as img:
                    img.depth = 8
                    img.save(filename=snap)

                if self.pic_ext == "png":
                    oxipng.optimize(snap, level=6)

            snapshots.append(snap)
            progress.update(generate, advance=1)

        if not self.args.skip_upload:
            upload = progress.add_task(
                "[bold magenta]Uploading snapshots[white]", total=self.pic_num
            )

            snapshots = [x for x in snapshots if x.stat().st_size < 5 * 1024 * 1024]
            snapshots_link = asyncio.run(upload_files(snapshots, upload, progress))

            for link in snapshots_link:
                self.description += f"![]({link})\n"
                images.add(
                    f"[not bold cornflower_blue][link={link}]{link}[/link][white /not bold]"
                )

        return images


def get_public_trackers(self):
    if self.add_pub_trackers:
        with httpx.Client(transport=transport) as client:
            try:
                response = client.get(
                    "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt"
                )
                response.raise_for_status()
                self.announces.extend([x for x in response.text.splitlines() if x])
            except httpx.HTTPError as e:
                eprint(str(e))


def create_torrent(self, name: str, filename: Path, overwrite: bool) -> bool:
    torrent_file = Path(f"{self.cache_dir}/{name}.torrent")
    if torrent_file.is_file():
        if overwrite:
            wprint("Torrent file already exists, removing...")
            torrent_file.unlink()
        else:
            iprint("Torrent file already exists, using existing file...")
            return True

    iprint("Creating torrent...", 0)

    get_public_trackers(self)

    torrent = Torrent(
        filename,
        trackers=self.announces,
        source="nyaa.si",
        creation_date=None,
        created_by="",
        exclude_regexs=[r".*\.(ffindex|jpg|nfo|png|srt|torrent|txt|json)$"],
    )

    with Progress(
        TextColumn("[progress.description]{task.description}[/]"),
        "•",
        BarColumn(),
        CustomTransferSpeedColumn(),
        TaskProgressColumn(),
        TextColumn("Time:"),
        TimeRemainingColumn(elapsed_when_finished=True),
    ) as progress:
        files = []

        def update_progress(
            torrent: Torrent, filepath: str, pieces_done: int, pieces_total: int
        ) -> None:
            if filepath not in files:
                progress.console.print(
                    f"[bold white]Hashing [not bold white]{Path(filepath).name}..."
                )
                files.append(filepath)

            progress.update(
                create,
                completed=pieces_done * torrent.piece_size,
                total=pieces_total * torrent.piece_size,
            )

        create = progress.add_task(
            description="[bold magenta]Torrent creating[not bold white]"
        )
        #  torrent.randomize_infohash = True
        torrent.generate(callback=update_progress, interval=1)
        torrent.write(torrent_file)

    return True


def rentry_upload(self) -> dict:
    with Session(client_identifier="firefox_120") as session:
        res = session.get(
            url="https://rentry.co",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
                "Origin": "https://rentry.co",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            allow_redirects=True,
        )

        try:
            res = session.post(
                "https://rentry.co/api/new",
                headers={
                    "Referer": "https://rentry.co",
                },
                data={
                    "csrfmiddlewaretoken": session.cookies["csrftoken"],
                    "edit_code": self.edit_code if self.edit_code else "",
                    "text": self.text,
                    "url": "",
                },
            )
        except httpx.HTTPError as e:
            eprint(str(e), True)

        if res.status_code != 200:
            eprint(f"Failed to upload to rentry.co! ({res.status_code})", True)

        try:
            res = res.json()
        except Exception as e:
            eprint(f"{str(e)}, {res.text}", True)

    return res


def get_return(lang: str, track_name: Optional[str] = None) -> str:
    if track_name:
        if track_name in {"CC", "SDH", "Forced", "Dubtitle"}:
            return f"**{lang}** [{track_name}]"
        if r := re.search(r"(.*) \((CC|SDH|Forced|Dubtitle)\)", track_name):
            return f"**{lang}** ({r[1]}) [{r[2]}]"
        else:
            return f"**{lang}** ({track_name})"
    else:
        return f"**{lang}**"


def get_track_info(data: dict) -> str:
    lang = data.get("Language")
    if not lang:
        lang = "Und"
        wprint("One track has unknown language!")
    else:
        lang = Language.get(lang).display_name()
    track_name = data.get("Title") or None

    if track_name and "(" in lang:
        lang = lang.split(" (")[0]
        return get_return(lang, track_name)
    elif "(" in lang:
        lang = lang.split(" (")[0]
        return get_return(lang)
    elif track_name:
        return get_return(lang, track_name)
    else:
        return get_return(lang)


def get_description(mediainfo: list) -> tuple[str, list[str], list[str]]:
    video_info = ""
    audio_info: list[str] = []
    subtitles_info: list[str] = []

    video_t_num = 0

    for info in mediainfo:
        if info["@type"] == "Video":
            v_bitrate = ""
            try:
                b_raw = float(float(info["StreamSize"]) * 8 / float(info["Duration"]))
                if b_raw / 1000 < 10000:
                    b = f"{b_raw / 1000:.0f} kbps"
                else:
                    b = f"{b_raw / 1000000:.2f} Mbps"
                v_bitrate = f" @ **{b}**"
            except KeyError:
                wprint("Couldn't get video bitrate!")

            codec = ""
            if codec_ := info.get("InternetMediaType"):
                codec = codec_.split("/")[1] + " "
            elif codec_ := info.get("Format"):
                codec = codec_
            level = f'**{info.get("Format_Profile")}@L{info.get("Format_Level")}**'
            if "None" in level:
                level = ""
            else:
                codec = codec + " "

            video_info += ", ".join(
                [
                    x
                    for x in [
                        f"**{codec}{level}**",
                        f'**{info.get("Width")}x{info.get("Height")}**' + v_bitrate,
                        f'**{info.get("FrameRate_String")}**',
                    ]
                    if x
                ]
            )

            video_t_num += 1

        if info["@type"] == "Audio":
            a_bitrate = ""
            try:
                a_bitrate = f" @ {round(float(info['BitRate'])/1000)} kbps"
            except KeyError:
                wprint("Couldn't get audio bitrate!")
            atmos = "JOC" in info.get("Format_AdditionalFeatures", "")

            audio_info += [
                ", ".join(
                    [
                        x
                        for x in [
                            get_track_info(info),
                            f'{AUDIO_CODEC_MAP.get(info["Format"], info["Format"])}'
                            + f'{CHANNEL_MAP.get(info.get("Channels", ""), "?")}'
                            + f'{" Atmos" if atmos else ""}'
                            + a_bitrate,
                        ]
                        if x
                    ]
                )
            ]

        if info["@type"] == "Text":
            subtitles_info += [
                ", ".join(
                    [
                        x
                        for x in [
                            get_track_info(info),
                            f'{SUB_CODEC_MAP.get(info["Format"], info["Format"])}',
                        ]
                        if x
                    ]
                )
            ]

    if video_t_num != 1:
        eprint(f"There is multiple videos in the file ({video_t_num})!", True)

    if not audio_info:
        eprint("Unable to determine audio language!", True)

    if not subtitles_info:
        subtitles_info = []
        wprint("Unable to determine subtitle language!")

    return video_info, audio_info, subtitles_info


def get_mal_link(myanimelist, name_to_mal) -> Optional[Anime]:
    mal_data: Optional[Anime] = None

    if myanimelist:
        with console.status(
            "[bold magenta]Getting MyAnimeList info form input link..."
        ) as _:
            malid = int(str(myanimelist).split("/")[4])
            while not mal_data:
                mal_data = Anime(malid)
    else:
        data: list | None = None
        with console.status(
            "[bold magenta]Searching MyAnimeList link form input name..."
        ) as _:
            while not data:
                data = AnimeSearch(name_to_mal).results[:10]
            for x in data:
                anime = Anime(x.mal_id)
                name_in = (name_to_mal or "").casefold()
                name_en = (anime.title_english or "").casefold()
                name_ori = (anime.title or "").casefold()
                if (similar(name_en, name_in) >= 0.75) or (
                    similar(name_ori, name_in) >= 0.75
                ):
                    mal_data = anime
                    break
                if not mal_data:
                    mal_data = Anime(data[0].mal_id)

    iprint(
        "[bold magenta]Myanimelist page successfuly found![not bold white]",
        up=0,
        down=0,
    )

    return mal_data


def similar(x, y):
    return SequenceMatcher(None, x, y).ratio()


def tgpost(self, ms=None):
    if ms:
        with httpx.Client(transport=transport) as client:
            client.post(
                url=f"https://api.telegram.org/bot{self.tg_token}/sendMessage",
                params={
                    "text": ms,
                    "chat_id": self.tg_id,
                    "parse_mode": "html",
                    "disable_web_page_preview": True,
                },
            )


class RParse(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("formatter_class", lambda prog: CustomHelpFormatter(prog))
        super().__init__(*args, **kwargs)

    def _print_message(self, message: str, file: IO[str] | None = None) -> None:
        if "error" in message:
            lprint(f"[white not bold]{message}")
        if message:
            if message.startswith("usage"):
                message = re.sub(
                    r"(-[a-z-A-Z]+\s*|\[)([A-Z-_:]+)(?=]|,|\s\s|\s\.)",
                    r"\1[bold color(231)]\2[/]",
                    message,
                )
                message = re.sub(r"((-|--)[a-z-A-Z]+)", r"[green]\1[/]", message)
                message = message.replace("usage", "[yellow]USAGE[/]")
                message = message.replace(" file ", "[bold magenta] file [/]", 2)
                message = message.replace(self.prog, f"[bold cyan]{self.prog}[/]")
            message = f"{message.strip()}"
            if "options:" in message:
                m = message.split("options:")
                if "positional arguments:" in m[0]:
                    op = m[0].split("positional arguments:")
                    pa = op[1].strip().replace("}", "").replace("{", "").split(",")
                    pa = f'[green]{"[/], [green]".join(pa)}[/]'
                    lprint(op[0].strip().replace(op[1].strip(), pa))
                    lprint("")
                    console.print(
                        Panel.fit(
                            f"  {pa}",
                            border_style="dim",
                            title="Positional arguments",
                            title_align="left",
                        )
                    )
                    lprint("")
                else:
                    lprint(m[0].strip())
                    lprint("")

                console.print(
                    Panel.fit(
                        f"  {m[1].strip()}",
                        border_style="dim",
                        title="Options",
                        title_align="left",
                    )
                )


def cat_help() -> None:
    categories_help = Tree("[chartreuse2]Available categories:[white /not bold]")
    cats = [
        "Anime - English-translated",
        "Anime - Non-English-translated",
        "Anime - Raw",
        "Live Action - English-translated",
        "Live Action - Non-English-translated",
        "Live Action - Raw",
        "Anime - Anime Music Video",
    ]

    for num, x in enumerate(cats, start=1):
        categories_help.add(f"[{num}] [cornflower_blue not bold]{x}[white /not bold]")

    rprint(categories_help)


class CustomHelpFormatter(argparse.RawTextHelpFormatter):
    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("max_help_position", 80)
        super().__init__(*args, **kwargs)

    def _format_action_invocation(self, action: argparse.Action) -> str:
        if not action.option_strings or action.nargs == 0:
            return super()._format_action_invocation(action)
        default = self._get_default_metavar_for_optional(action)
        args_string = self._format_args(action, default)
        return ", ".join(action.option_strings) + " " + args_string


class Config:
    def __init__(self):
        self.dirs = dirs
        self.config_path = Path(dirs.user_config_path / "nyaaup.yaml")
        self.cookies_path = Path(dirs.user_config_path / "cookies.txt")
        self.cookies = {}
        self.yaml = YAML()

        self.get_cookies()

    @property
    def get_dirs(self):
        return self.dirs

    def get_cookies(self):
        if self.cookies_path.exists():
            data = self.cookies_path.read_text().splitlines()
            for x in data:
                if (
                    x
                    and not x.startswith("#")
                    and (values := x.split("\t"))
                    and values[-2] != "__ddg9__"
                ):
                    self.cookies[values[-2]] = values[-1]

    def create(self, exit=False):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(
            Path(__file__).resolve().parent.with_name("nyaaup.yaml.example"),
            self.config_path,
        )

        eprint(f"Config file doesn't exist, created to: {self.config_path}", fatal=exit)

        return self.load(exit)

    def load(self, exit=True):
        try:
            return self.yaml.load(self.config_path)
        except FileNotFoundError:
            return self.create(exit)

    @staticmethod
    def get_cred(cred: str) -> SimpleNamespace | NoReturn:
        if cred == "user:pass":
            eprint("Set valid credentials!", True)
        if return_cred := re.fullmatch(r"^([^:]+?):([^:]+?)(?::(.+))?$", cred):
            cred_ = return_cred.groups()
            return SimpleNamespace(**{"username": cred_[0], "password": cred_[1]})
        else:
            eprint("Incorrect credentials format!  (Format: `user:pass`)", True)

    def update(self, data):
        try:
            self.yaml.dump(data, self.config_path)
        except FileNotFoundError:
            self.create()
            self.update(data)

        lprint("[bold green]\nConfig successfully updated![white]")
