from __future__ import annotations

import subprocess
import json

from platformdirs import PlatformDirs
from pymediainfo import MediaInfo
from rich.console import Console
from pathlib import Path

dirs = PlatformDirs(appname="nyaaup", appauthor=False)
console = Console()


class Torrent:
    def __init__(
        self, name: str,
        path: Path,
        display_name: str,
        category,
        information,
        temp_path,
        anime,
        complete,
        hidden,
        anonymous,
        name_to_mal,
    ):
        self.path = path
        self.name = name
        self.mediainfo: MediaInfo = None
        self.mediainfo_json: dict = dict()
        
        self.get_mediainfo(self)

    def get_mediainfo(self):
        with console.status("[bold magenta]MediaInfo parseing...") as status:
            self.mediainfo_json = json.loads(subprocess.run(
            ["mediainfo",  "--ParseSpeed=1.0", "-f", "--output=JSON", self.path], capture_output=True, encoding="utf-8").stdout)["media"]["track"]

            self.mediainfo = MediaInfo.parse(self.path, output="", full=False).replace(
                str(self.path), str(self.path.name))

