import requests
import humanize
import random
import subprocess
import sys
import re
import json
from json import loads
import shutil
import argparse
from rich.padding import Padding
from rich.console import Console
from typing import Any, IO, Literal, NoReturn, overload
from ruamel.yaml import YAML
import oxipng
from torf import Torrent
from pathlib import Path
from wand.image import Image
from langcodes import Language
from mal import AnimeSearch, Anime
from platformdirs import PlatformDirs
from rich.tree import Tree
from rich.text import Text
from rich import print
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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from rich.panel import Panel
import torf
import hashlib
import bencodepy as bcp

dirs = PlatformDirs(appname="nyaaup", appauthor=False)
console = Console()

MAP = {
    # subtitle codecs
    "SubRip/SRT": "SRT",
    "SubStationAlpha": "ASS",
    # audio codecs
    "E-AC-3": "DDP",
    "AAC": "AAC",
    "E-AC": "DD",
    # channels
    1: 1.0,
    2: 2.0,
    6: 5.1,
    8: 7.1,
}


class RParse(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("formatter_class",
                          lambda prog: CustomHelpFormatter(prog))
        super().__init__(*args, **kwargs)

    def _print_message(self, message: str, file: IO[str] | None = None) -> None:
        if "error" in message:
            print(f'[white not bold]{message}')
        if message:
            if message.startswith("usage"):
                message = re.sub(
                    r"(-[a-z-A-Z]+\s*|\[)([A-Z-_:]+)(?=]|,|\s\s|\s\.)", r"\1[bold color(231)]\2[/]", message)
                message = re.sub(
                    r"((-|--)[a-z-A-Z]+)", r"[green]\1[/]", message)
                message = message.replace("usage", "[yellow]USAGE[/]")
                message = message.replace(
                    " file ", "[bold magenta] file [/]", 2)
                message = message.replace(
                    self.prog, f"[bold cyan]{self.prog}[/]")
            message = f"{message.strip()}"
            if "options:" in message:
                m = message.split("options:")
                if "positional arguments:" in m[0]:
                    op = m[0].split("positional arguments:")
                    pa = op[1].strip().replace(
                        "}", "").replace("{", "").split(",")
                    pa = f'[green]{"[/], [green]".join(pa)}[/]'
                    print(op[0].strip().replace(op[1].strip(), pa))
                    print('')
                    console.print(
                        Panel(
                            f"  {pa}", border_style="dim", title="Positional arguments", title_align="left"
                        )
                    )
                    print('')
                else:
                    print(m[0].strip())
                    print('')

                console.print(
                    Panel(
                        f"  {m[1].strip()}", border_style="dim", title="Options", title_align="left"
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


class log():
    def print(
            text: Any = "", highlight: bool = False, file: IO[str] = sys.stdout, flush: bool = False, **kwargs: Any) -> None:
        with Console(highlight=highlight) as console:
            console.print(text, **kwargs)
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
            print()
        print(f"[bold color(231) on red]ERROR:[/] [red]{text}[/]")
        if fatal:
            sys.exit(exit_code)
        return None

    def info(text: str, up: int = 1, down: int = 1) -> None:
        text = Padding(f"[bold green]{text}[white]",
                       (up, 0, down, 0), expand=False)
        print(text)

    def wprint(text: str) -> None:
        if text.startswith("\n"):
            text = text.lstrip("\n")
            print()
        print(f"[bold color(231) on yellow]WARNING:[/] [yellow]{text}[/]")


class Config():
    def __init__(self):
        self.dirs = dirs
        self.config_path = Path(dirs.user_config_path / "nyaaup.ymal")
        self.yaml = YAML()

    def get_dirs(self):
        return self.dirs

    def creat(self, exit: bool = False):
        shutil.copy(Path(__file__).resolve().parent.parent.with_name(
            'nyaaup.yaml.example'), self.config_path)
        log.eprint(
            f"Config file doesn't exist, created to: {self.config_path}", exit)

    def load(self):
        try:
            return self.yaml.load(self.config_path)
        except:
            self.creat(True)

    def add(self, text: str):
        credential = re.fullmatch(r"^([^:]+?):([^:]+?)(?::(.+))?$", text)
        if credential:
            try:
                data = self.yaml.load(self.config_path)
            except:
                self.creat()
                data = self.yaml.load(self.config_path)
        else:
            log.eprint(
                "No credentials found in text. Format: `username:password`")
        data["credentials"]["username"] = credential.groups()[0]
        data["credentials"]["password"] = credential.groups()[1]
        self.yaml.dump(data, self.config_path)
        log.print("[bold green]\nCredential successfully added![white]")
        sys.exit(1)


class GetTracksInfo():
    def __init__(self, data) -> None:
        self.track_info = []
        self.lang = Language.get(data["properties"].get("language_ietf")
                                 or data["properties"].get("language")).display_name()
        self.track_name = data["properties"].get("track_name") or None

    def greturn(self, lang: str, track_name: str = None) -> str:
        if track_name:
            return f"**{lang}** ({track_name})"
        else:
            return f"**{lang}**"

    def get_info(self) -> str:
        if self.track_name and "(" in self.lang:
            self.lang = self.lang.split(" (")[0]
            return self.greturn(self.lang, self.track_name)
        elif "(" in self.lang:
            self.lang = self.lang.split(" (")[0]
            return self.greturn(self.lang)
        elif self.track_name:
            return self.greturn(self.lang, self.track_name)
        else:
            return self.greturn(self.lang)


def generate_snapshots(self, input: Path, name: str, mediainfo_obj) -> list:

    with Progress(
        TextColumn("[progress.description]{task.description}[/]"),
        "•",
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TextColumn("Time:"),
        TimeRemainingColumn(elapsed_when_finished=True),
    ) as progress:
        task1 = progress.add_task(
            "[bold magenta]Generating snapshots[not bold white]", total=self.pic_num)
        while not progress.finished:
            snapshots = []
            num_snapshots = self.pic_num + 1
            for x in range(1, num_snapshots):

                snap = f'{self.cache_dir}/{name}_{x}.png'
                duration = float(mediainfo_obj.video_tracks[0].duration) / 1000
                interval = duration / (num_snapshots + 1)
                subprocess.run([
                    "ffmpeg",
                    "-y",
                    "-v", "error",
                    "-ss", str(
                        random.randint(
                            round(interval * 10), round(interval * 10 * num_snapshots)) / 10
                    ),
                    "-i", input,
                    "-vf", "scale='max(sar,1)*iw':'max(1/sar,1)*ih'",
                    "-frames:v", "1",
                    snap,
                ], check=True)
                with Image(filename=snap) as img:
                    img.depth = 8
                    img.save(filename=snap)
                oxipng.optimize(snap)
                snapshots.append(snap)
                progress.update(task1, advance=1)

    return snapshots


def image_upload(self, snapshots: list, description: str) -> any:

    def image_uploader(image_path: Path) -> str:
        with open(image_path, 'rb') as file:
            kek_request = requests.post(
                'https://kek.sh/api/v1/posts', files={'file': file})
            return kek_request.json()["filename"]

    images = Tree("[bold white]Images[not bold]")

    with Progress(
        TextColumn("[progress.description]{task.description}[/]"),
        "•",
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TextColumn("Time:"),
        TimeRemainingColumn(elapsed_when_finished=True),
    ) as progress:
        task1 = progress.add_task(
            "[bold magenta]Uploading snapshots[white]", total=self.pic_num)
        for i in snapshots:
            image_link = image_uploader(i)
            description += f'![](https://i.kek.sh/{image_link})\n'
            images.add(
                f"[not bold cornflower_blue]https://i.kek.sh/{image_link}[white /not bold]")
            progress.update(task1, advance=1)

    return images, description


def creat_torrent(self, name, filename) -> bool:
    if Path((f'{self.cache_dir}/{name}.torrent')).is_file():
        """
        bencodepy = bcp.Bencode(encoding="utf-8", encoding_fallback="value")
        tor = open(f'{self.cache_dir}/{name}.torrent', mode='rb')
        tor = tor.read()
        torrent_file = bencodepy.decode(tor)
        print(hashlib.sha1(torrent_file["info"]["pieces"]).hexdigest())
        if update := torrent_file.update():
            info = torrent_file.encode(update["info"])
            info_hash = hashlib.sha1(info).hexdigest()
        item = bencodepy.decode(tor)
        #info_hash = hashlib.sha1(infos).hexdigest()

        tor = tor.read()
        torrent_file = bencodepy.decode(tor)
        if update := torrent_file.update():
            if new_torrent := torrent_file.encode(update):
                info = torrent_file.encode(update["info"])
                info_hash = hashlib.sha1(info).hexdigest()
        item = bencodepy.decode(tor)
        infos = item.encode(item["info"])
        print(infos)
        info_hash = hashlib.sha1(infos).hexdigest()
        print(info_hash)
        t = Torrent.read(f'{cache_dir}/{name}.torrent')
        print(t)
        sys.exit(1)

        torrent.reuse(filename)
        try:
            torrent.validate()
        except torf.MetainfoError:
            print(f'[red1]Torrent file is invalid, recreating[white]')
        else:
            torrent.trackers = ['http://nyaa.tracker.wf:7777/announce']
            torrent.source = 'nyaa.si'
            torrent.write(f'{cache_dir}/{name}.torrent')
        """
        log.wprint(f"Torrent file already exists, removing...")
        Path(f'{self.cache_dir}/{name}.torrent').unlink()
    log.info("Creating torrent...", 0)

    torrent = Torrent(
        filename,
        trackers=['http://nyaa.tracker.wf:7777/announce'],
        source='nyaa.si',
        creation_date=None,
        created_by=None,
        exclude_regexs=[r".*\.(ffindex|jpg|nfo|png|srt|torrent|txt)$"],
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

        def update_progress(torrent: Torrent, filepath: str, pieces_done: int, pieces_total: int) -> None:
            if filepath not in files:
                progress.console.print(
                    f'[bold white]Hashing [not bold white]{Path(filepath).name}...')
                files.append(filepath)

            progress.update(
                task, completed=pieces_done * torrent.piece_size, total=pieces_total * torrent.piece_size
            )
        task = progress.add_task(
            description="[bold magenta]Torrent creating[not bold white]")
        # torrent.randomize_infohash = True
        torrent.generate(callback=update_progress, interval=1)
        torrent.write(f'{self.cache_dir}/{name}.torrent')

    return True


def rentry_upload(self) -> dict:

    # get csrftoken
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    session.get(url="https://rentry.co")

    try:
        res = session.post(
            'https://rentry.co/api/new',
            headers={
                "Referer": "https://rentry.co"
            },
            data={
                'csrfmiddlewaretoken': session.cookies['csrftoken'],
                'url': self.url,
                'edit_code': self.edit_code,
                'text': self.text
            },
        ).json()
    except requests.HTTPError as e:
        raise log.eprint(e.response, True)

    return res


def get_description(self, input: Path, mediainfo_obj, mediainfo_obj_xml) -> list:

    video_info = []
    audio_info = []
    subtitles_info = []

    if input.suffix == ".mkv":
        mediainfo = json.loads(subprocess.run(
            ["mkvmerge", "-J", input], capture_output=True, encoding="utf-8").stdout)
        video_t_num = 0
        audio_t_num = 0

        for info in mediainfo["tracks"]:

            if not video_info:
                video_info.append(
                    f'**{mediainfo_obj_xml.video_tracks[0].format} {mediainfo_obj_xml.video_tracks[0].format_profile}**')
            if info["type"] == "video":
                video_t_num += 1
                video_info.append(
                    f'**{info["properties"].get("pixel_dimensions")}**')
            if info["type"] == "audio":
                temp = []
                temp.append(GetTracksInfo(info).get_info())
                at = MAP.get(str(mediainfo_obj_xml.audio_tracks[audio_t_num].format))
                if mediainfo_obj_xml.audio_tracks[audio_t_num].format_additionalfeatures and "JOC" in mediainfo_obj_xml.audio_tracks[audio_t_num].format_additionalfeatures:
                    at += "Atmos"
                temp.append(at)
                temp.append(f'{MAP.get(info["properties"]["audio_channels"])}')
                try:
                    temp.append(
                        f"~{round(mediainfo_obj.audio_tracks[audio_t_num].bit_rate/1000)} kbps")
                except:
                    log.wprint(f"Couldn't get audio bitrate!")
                audio_info.append(" | ".join(temp))
                audio_t_num += 1
            if info["type"] == "subtitles":
                temp = []
                temp.append(GetTracksInfo(info).get_info())
                temp.append(f'{MAP.get(info["codec"])}')
                subtitles_info.append(" | ".join(temp))

        if video_t_num != 1:
            raise log.eprint(
                f"More than 1 video found in file! ({video_t_num})", True)

        if not audio_info:
            raise log.eprint(f"Unable to determine audio language!", True)

        if not subtitles_info:
            subtitles_info.append('N/A')
            log.wprint(f"Unable to determine subtitle language!")
        video_info.append(
            f'**{mediainfo_obj.video_tracks[0].frame_rate} FPS**')
        try:
            video_info.append(
                f'**~{mediainfo_obj.video_tracks[0].bit_rate//1000} kbps**')
        except:
            log.wprint(f"Couldn't get video bitrate!")
    return video_info, audio_info, subtitles_info


def get_mal_link(anime, myanimelist, name) -> str:
    if anime:
        search = False
        if myanimelist:
            with console.status("[bold magenta]Getting MyAnimeList info form input link...") as status:
                malid = str(myanimelist).split("/")[4]
                while not search:
                    search = Anime(malid)
                name_to_mal = search.title
        else:
            with console.status("[bold magenta]Searching MyAnimeList link form input name...") as status:
                name_to_mal = re.sub(r"\.S\d+.*", "", name).replace(".", " ")
                while not search:
                    search = AnimeSearch(name_to_mal).results[0]
        log.info(
            "[bold magenta]Myanimelist page successfuly found![not bold white]", up=0, down=0)

    return search, name_to_mal
