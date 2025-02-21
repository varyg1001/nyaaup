import subprocess
from pathlib import Path

import httpx
from rich.progress import (BarColumn, Progress, TaskProgressColumn, TextColumn,
                           TimeRemainingColumn)
from torf import Torrent

from nyaaup.utils import CustomTransferSpeedColumn
from nyaaup.utils.collections import as_list
from nyaaup.utils.logging import eprint, iprint, wprint


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


def create_torrent(ctx, name: str, filename: Path, overwrite: bool, torrent_tool: str) -> bool:
    if torrent_tool == "torrenttools":
        result = create_torrent_torrenttools(ctx, name, filename, overwrite)
    else:
        result = create_torrent_torf(ctx, name, filename, overwrite)

    return result


def create_torrent_torrenttools(ctx, name: str, filename: Path, overwrite: bool) -> bool:
    torrent_file = Path(f"{ctx.cache_dir}/{name}.torrent")

    if torrent_file.exists():
        if overwrite:
            wprint("Torrent file exists, removing...")
            torrent_file.unlink()
        else:
            iprint("Using existing torrent file...")
            return True

    iprint("Creating torrent...", 0)

    if ctx.add_pub_trackers:
        ctx.announces = get_public_trackers(ctx.announces)

    subprocess.run(
        [
            "torrenttools",
            "create",
            str(filename),
            "--no-created-by",
            "--no-creation-date",
            "--exclude",
            r".*\.(ffindex|jpg|nfo|png|torrent|txt|json)$",
            "--announce",
            " ".join(as_list(ctx.announces)),
            "-s",
            "nyaa.si",
            "--piece-size",
            "16M",
            "--output",
            str(torrent_file),
        ],
        check=True,
    )
    print()

    return torrent_file.exists()


def create_torrent_torf(ctx, name: str, filename: Path, overwrite: bool) -> bool:
    torrent_file = Path(f"{ctx.cache_dir}/{name}.torrent")

    if torrent_file.is_file():
        if overwrite:
            wprint("Torrent file exists, removing...")
            torrent_file.unlink()
        else:
            iprint("Using existing torrent file...")
            return True

    iprint("Creating torrent...", 0)

    if ctx.add_pub_trackers:
        ctx.announces = get_public_trackers(ctx.announces)

    torrent = Torrent(
        filename,
        trackers=ctx.announces,
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
