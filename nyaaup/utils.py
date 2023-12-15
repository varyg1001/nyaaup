from __future__ import annotations

import humanize
import random
import subprocess
import sys
import re
import os
import shutil
import argparse
from pathlib import Path
import httpx

from rich.padding import Padding
from rich.console import Console
from typing import Any, IO, Literal, NoReturn, overload, Optional, Iterable
from ruamel.yaml import YAML
import oxipng
from torf import Torrent
from wand.image import Image
from langcodes import Language
from mal import AnimeSearch, Anime
from platformdirs import PlatformDirs
from rich.tree import Tree
from rich.text import Text
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
console = Console()
transport = httpx.HTTPTransport(retries=5)

MAP: dict = {
    # subtitle codecs
    "UTF-8": "SRT",
    "ASS": "ASS",
    # channels
    "1": "1.0",
    "2": "2.0",
    "6": "5.1",
    "8": "7.1",
}


class RParse(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("formatter_class", lambda prog: CustomHelpFormatter(prog))
        super().__init__(*args, **kwargs)

    def _print_message(self, message: str, file: IO[str] | None = None) -> None:  # noqa: E501
        if "error" in message:
            lprint(f"[white not bold]{message}")
        if message:
            if message.startswith("usage"):
                message = re.sub(
                    r"(-[a-z-A-Z]+\s*|\[)([A-Z-_:]+)(?=]|,|\s\s|\s\.)",
                    r"\1[bold color(231)]\2[/]",
                    message,
                )  # noqa: E501
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
                            title_align="left",  # noqa: E501
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
                        title_align="left",  # noqa: E501
                    )
                )


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


class Config:
    def __init__(self):
        self.dirs = dirs
        self.config_path = Path(dirs.user_config_path / "nyaaup.ymal")
        self.yaml = YAML()

    def get_dirs(self):
        return self.dirs

    def create(self, exit: Optional[bool] = False):
        shutil.copy(
            Path(__file__).resolve().parent.with_name("nyaaup.yaml.example"),
            self.config_path,
        )
        eprint(f"Config file doesn't exist, created to: {self.config_path}", fatal=exit)  # noqa: E501

    def load(self):
        try:
            return self.yaml.load(self.config_path)
        except FileNotFoundError:
            self.create(True)

    @staticmethod
    def get_cred(cred: str):
        if cred == "user:pass":
            eprint("Set valid credentials!", True)
        if return_cred := re.fullmatch(r"^([^:]+?):([^:]+?)(?::(.+))?$", cred):
            return return_cred.groups()
        else:
            eprint("Incorrect credentials format!", True)

    def add(self, text: str):
        credential = self.get_cred(text)
        data = dict()
        if credential:
            try:
                data = self.yaml.load(self.config_path)
            except FileNotFoundError:
                self.create()
                data = self.yaml.load(self.config_path)
        else:
            eprint("No credentials found in text. Format: `user:pass`")
        data["credentials"] = text
        self.yaml.dump(data, self.config_path)
        lprint("[bold green]\nCredential successfully added![white]")
        sys.exit(1)


class GetTracksInfo:
    def __init__(self, data: dict):
        self.track_info = []
        lang = data.get("Language")
        if not lang:
            self.lang = "Und"
            wprint("One track has unknown language!")
        else:
            self.lang = Language.get(lang).display_name()
        self.track_name = data.get("Title") or None

    def get_return(self, lang: str, track_name: Optional[str] = None) -> str:
        if track_name:
            if track_name in {"SDH", "Forced"}:
                return f"**{lang}** [{track_name}]"
            if r := re.search(r"(.*) \((SDH|Forced)\)", track_name):
                return f"**{lang}** ({r[1]}) [{r[2]}]"
            else:
                return f"**{lang}** ({track_name})"
        else:
            return f"**{lang}**"

    def get_info(self) -> str:
        if self.track_name and "(" in self.lang:
            self.lang = self.lang.split(" (")[0]
            return self.get_return(self.lang, self.track_name)
        elif "(" in self.lang:
            self.lang = self.lang.split(" (")[0]
            return self.get_return(self.lang)
        elif self.track_name:
            return self.get_return(self.lang, self.track_name)
        else:
            return self.get_return(self.lang)


def snapshot(self, input: Path, name: str, mediainfo: list) -> Tree:
    def up(image_path: Path) -> str:
        with open(image_path, "rb") as file:
            res = httpx.post("https://kek.sh/api/v1/posts", files={"file": file})

            return f'https://i.kek.sh/{res.json()["filename"]}'

    images = Tree("[bold white]Images[not bold]")
    
    if self.in_f.is_dir():
        files = sorted([*self.in_f.glob("*.mkv"), *self.in_f.glob("*.mp4")])
    elif self.in_f.is_file():
        files = [self.in_f]

    num_snapshots = self.pic_num
    if self.in_f.is_dir():
        num_snapshots = len(files)

    orig_files = files[:]
    i = 2
    while len(files) < num_snapshots:
        files = flatten(zip(*([orig_files] * i)))
        i += 1

    last_file = None
    with Progress(
        TextColumn("[progress.description]{task.description}[/]"),
        "•",
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TextColumn("Time:"),
        TimeRemainingColumn(elapsed_when_finished=True, compact=True),
    ) as progress:
        snapshots = []
        num_snapshots = self.pic_num + 1

        generate = progress.add_task(
            "[bold magenta]Generating snapshots[not bold white]", total=self.pic_num
        )

        for x in range(1, num_snapshots):
            snap = f"{self.cache_dir}/{name}_{x}.{self.pic_ext}"
            if not Path(snap).is_file():
                duration = float(mediainfo[0].get("Duration"))
                interval = duration / (num_snapshots + 1)
                j = x
                if last_file != files[i]:
                    j = 0
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-v",
                        "error",
                        "-ss", str(
                            random.randint(round(interval * 10), round(interval * 10 * num_snapshots)) / 10
                            if self.random_snapshots
                            else str(interval * (j + 1))  # noqa: E501
                        ),
                        "-i",
                        input,
                        "-vf",
                        "scale='max(sar,1)*iw':'max(1/sar,1)*ih'",
                        "-frames:v",
                        "1",
                        snap,
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

            for x in range(1, num_snapshots):
                snap = snapshots[x - 1]
                file_size = os.path.getsize(snap)

                if file_size > 5 * 1024 * 1024:  # 5MB in bytes
                    wprint(f"Skipping snapshot {snap} as its size is more than 5MB")  # noqa: E501
                else:
                    link = up(snapshots[x - 1])
                    self.description += f"![]({link})\n"
                    images.add(
                        f"[not bold cornflower_blue][link={link}]{link}[/link][white /not bold]"
                    )  # noqa: E501

                progress.update(upload, advance=1)

        return images


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

    torrent = Torrent(
        filename,
        trackers=get_public_trackers(self),
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
                )  # noqa: E501
                files.append(filepath)

            progress.update(
                create,
                completed=pieces_done * torrent.piece_size,
                total=pieces_total * torrent.piece_size,  # noqa: E501
            )

        create = progress.add_task(
            description="[bold magenta]Torrent creating[not bold white]"
        )
        #  torrent.randomize_infohash = True
        torrent.generate(callback=update_progress, interval=1)
        torrent.write(torrent_file)

    return True


def rentry_upload(self) -> dict:
    with httpx.Client(transport=transport) as client:
        # get csrftoken
        client.get(url="https://rentry.co")

        try:
            res = client.post(
                "https://rentry.co/api/new",
                headers={"Referer": "https://rentry.co"},
                data={
                    "csrfmiddlewaretoken": client.cookies["csrftoken"],
                    "edit_code": self.edit_code,
                    "text": self.text,
                },
            ).json()
        except httpx.HTTPError as e:
            eprint(e.response, True)
        finally:
            client.close()

        return res


def get_description(mediainfo: list) -> tuple[str, list[str], list[str]]:
    video_info = ""
    audio_info: list[str] = []
    subtitles_info: list[str] = []

    video_t_num = 0

    for info in mediainfo:
        if info["@type"] == "Video":
            v_bitrate = ""
            try:
                v_bitrate = f' @ **{round(float(info["BitRate"])/1000)} kbps**'
            except KeyError:
                wprint("Couldn't get video bitrate!")

            video_info += ", ".join(
                [
                    x
                    for x in [
                        f'**{info.get("InternetMediaType").split("/")[1]} {info.get("Format_Profile")}@L{info.get("Format_Level")}**',
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
            atmos = info.get("Format_AdditionalFeatures")

            audio_info += [
                ", ".join(
                    [
                        x
                        for x in [
                            GetTracksInfo(info).get_info(),
                            f'{info.get("Format")}{" Atmos" if atmos and "JOC" in atmos else ""}',
                            f'{MAP.get(info["Channels"])}' + a_bitrate,
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
                            GetTracksInfo(info).get_info(),
                            f'{MAP.get(info["Format"])}',
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
        subtitles_info.append("N/A")
        wprint("Unable to determine subtitle language!")

    return video_info, audio_info, subtitles_info


def get_mal_link(anime, myanimelist, name) -> Optional[tuple[Anime, str]]:
    if anime:
        mal_data: Optional[Anime] = None
        name_to_mal = re.sub(r"\.S\d+.*", "", name)
        if name_to_mal == name:
            name_to_mal = re.sub(r"\.\d\d\d\d\..*", "", name)
        name_to_mal = name_to_mal.replace(".", " ")
        if myanimelist:
            with console.status(
                "[bold magenta]Getting MyAnimeList info form input link..."
            ) as _:  # noqa: E501
                malid: str = str(myanimelist).split("/")[4]
                while not mal_data:
                    mal_data = Anime(malid)
        else:
            with console.status(
                "[bold magenta]Searching MyAnimeList link form input name..."
            ) as _:  # noqa: E501
                while not mal_data:
                    mal_data = Anime(AnimeSearch(name_to_mal).results[0].mal_id)
        iprint(
            "[bold magenta]Myanimelist page successfuly found![not bold white]",
            up=0,
            down=0,
        )  # noqa: E501

        return mal_data, name_to_mal


def flatten(L: Iterable[Any]) -> list[Any]:
    # https://stackoverflow.com/a/952952/492203
    return [item for sublist in L for item in sublist]


def get_public_trackers(self) -> list[str]:
    trackers: list = ["http://nyaa.tracker.wf:7777/announce"]

    if self.add_pub_trackers:
        with httpx.Client(transport=transport) as client:
            try:
                response = client.get(
                    "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt"
                )
                trackers += [x for x in response.text.splitlines() if x]
            except httpx.HTTPError as e:
                eprint(e.response)

    return trackers
