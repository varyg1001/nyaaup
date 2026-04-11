import math
import subprocess
from functools import lru_cache
from pathlib import Path

import niquests
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from torf import Torrent

from nyaaup.utils import CustomTransferSpeedColumn
from nyaaup.utils.collections import as_list
from nyaaup.utils.logging import eprint, iprint, wprint


@lru_cache(maxsize=1)
def get_public_trackers() -> list[str]:
    try:
        res = niquests.get(
            "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt",
            retries=5,
        )
        res.raise_for_status()
        return list(filter(None, res.text.splitlines()))
    except niquests.RequestException as e:
        eprint(str(e))
        return []


def create_torrent(
    name: str,
    filename: Path,
    cache_dir: Path,
    announces: list[str],
    overwrite: bool,
    torrent_tool: str,
) -> bool:
    if torrent_tool == "torrenttools":
        result: bool = create_torrent_torrenttools(
            name, filename, cache_dir, announces, overwrite
        )
    else:
        result = create_torrent_torf(name, filename, cache_dir, announces, overwrite)

    return result


def create_torrent_torrenttools(
    name: str, filename: Path, cache_dir: Path, announces: list[str], overwrite: bool
) -> bool:
    torrent_file = Path(f"{cache_dir}/{name}.torrent")

    if torrent_file.exists():
        if overwrite:
            wprint("Torrent file exists, removing...")
            torrent_file.unlink()
        else:
            iprint("Using existing torrent file...")
            return True

    iprint("Creating torrent...", 0)

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
            " ".join(as_list(announces)),
            "--piece-size",
            "16M",
            "--output",
            str(torrent_file),
        ],
        check=True,
    )
    print()

    return torrent_file.exists()


def create_torrent_torf(
    name: str, filename: Path, cache_dir: Path, announces: list[str], overwrite: bool
) -> bool:
    torrent_file = Path(f"{cache_dir}/{name}.torrent")

    if torrent_file.is_file():
        if overwrite:
            wprint("Torrent file exists, removing...")
            torrent_file.unlink()
        else:
            iprint("Using existing torrent file...")
            return True

    iprint("Creating torrent...", 0)

    piece_size: int = 2**18

    if filename.is_file():
        total_bytes: int = filename.stat().st_size
    else:
        total_bytes = sum(f.stat().st_size for f in filename.rglob("*") if f.is_file())

    target_pieces = 1500
    exponent = max(18, min(24, round(math.log2(total_bytes / target_pieces))))
    piece_size = 2**exponent

    torrent = Torrent(
        filename,
        trackers=announces,
        creation_date=None,
        created_by=None,
        piece_size=piece_size,
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

        create = progress.add_task(
            description="[bold magenta]Creating torrent[not bold white]"
        )
        torrent.generate(callback=update_progress, interval=1)
        torrent.write(torrent_file)

    return True
