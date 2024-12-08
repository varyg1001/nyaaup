from pathlib import Path

import httpx
import humanize
from rich.progress import (BarColumn, Progress, TaskProgressColumn, TextColumn,
                           TimeRemainingColumn)
from rich.text import Text
from torf import Torrent

from nyaaup.utils.logging import eprint, iprint, wprint


class CustomTransferSpeedColumn(TimeRemainingColumn):
    def render(self, task):
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("--", style="progress.data.speed")
        return Text(
            f"{humanize.naturalsize(int(speed), binary=True)}/s",
            style="progress.data.speed",
        )


def get_public_trackers(announces: list) -> list:
    try:
        response = httpx.get(
            "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt"
        )
        response.raise_for_status()
        announces.extend([x for x in response.text.splitlines() if x])
        return announces
    except httpx.HTTPError as e:
        eprint(str(e))
        return announces


def create_torrent(self, name: str, filename: Path, overwrite: bool) -> bool:
    torrent_file = Path(f"{self.cache_dir}/{name}.torrent")

    if torrent_file.is_file():
        if overwrite:
            wprint("Torrent file exists, removing...")
            torrent_file.unlink()
        else:
            iprint("Using existing torrent file...")
            return True

    iprint("Creating torrent...", 0)

    if self.add_pub_trackers:
        self.announces = get_public_trackers(self.announces)

    torrent = Torrent(
        filename,
        trackers=self.announces,
        source="nyaa.si",
        creation_date=None,
        created_by="",
        exclude_regexs=[r".*\.(ffindex|jpg|nfo|png|torrent|txt|json)$"],
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

        create = progress.add_task(description="[bold magenta]Creating torrent[not bold white]")
        torrent.generate(callback=update_progress, interval=1)
        torrent.write(torrent_file)

    return True
