import asyncio
import random
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import aiofiles
import httpx
import oxipng
from rich.progress import (
    BarColumn, MofNCompleteColumn, Progress,
    TaskProgressColumn, TextColumn, TimeRemainingColumn,
)
from rich.tree import Tree
from tls_client import Session
from wand.image import Image

from nyaaup.utils.logging import wprint


if TYPE_CHECKING:
    from nyaaup.utils.uploader import Uploader

MAX_SIZE = 5 * 1024 * 1024  # 5 MB


async def _upload_image(image_path: Path, upload_task, progress, upload_config) -> str:
    async with aiofiles.open(image_path, "rb") as file:
        content = await file.read()
        async with httpx.AsyncClient() as client:
            res = await client.post(
                url="https://kek.sh/api/v1/posts",
                headers=upload_config.kek_headers,
                files={"file": content},
            )

            if res.status_code == 200:
                result = res.json()

                progress.update(upload_task, advance=1)

                return f"https://i.kek.sh/{result['filename']}"

            return ""


async def _upload_all_images(files, **kwargs):
    tasks = [_upload_image(file, **kwargs) for file in files]
    return await asyncio.gather(*tasks)


async def _generate_snapshot(
    num: int,
    upload_config: SimpleNamespace,
    input_file: Path,
    cache_dir,
    generate_task,
    interval,
    progress,
    num_snapshots,
) -> Path:
    out_path = Path(f"{cache_dir}/snapshot_{num}.{upload_config.pic_ext}")
    if not out_path.exists():
        timestamp = (
            random.randint(round(interval * 10), round(interval * 10 * num_snapshots))
            / 10
            if upload_config.random_snapshots
            else interval * (num + 1)
        )

        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            str(timestamp),
            "-i",
            str(input_file),
            "-vf",
            "scale='max(sar,1)*iw':'max(1/sar,1)*ih'",
            "-frames:v",
            "1",
            str(out_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise Exception(f"ffmpeg error: {stderr.decode()}")

        loop = asyncio.get_running_loop()

        def process_image():
            with Image(filename=out_path) as img:
                img.depth = 8
                img.save(filename=out_path)
            if upload_config.pic_ext == "png":
                oxipng.optimize(out_path, level=6)

        await loop.run_in_executor(None, process_image)

    progress.update(generate_task, advance=1)

    return out_path


async def _generate_all_snapshots(
    num_snapshots: int,
    **kwargs,
) -> list[Path]:
    tasks = [
        _generate_snapshot(x, num_snapshots=num_snapshots, **kwargs)
        for x in range(1, num_snapshots)
    ]
    return await asyncio.gather(*tasks)


def _get_snapshot_links(
    upload_config: SimpleNamespace | None = None,
    cache_dir: Path | str = "",
    input_file: Path | str = "",
    duration: float | int = 0,
) -> list[str]:
    if not input_file or not duration or not upload_config:
        return []

    if isinstance(input_file, str):
        input_file = Path(input_file)

    images: list[str] = []
    num_snapshots = upload_config.pic_num + 1
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
        generate_task = progress.add_task(
            "[bold magenta]Generating snapshots[not bold white]",
            total=num_snapshots,
        )

        interval = duration / (num_snapshots + 2)

        snapshots = asyncio.run(
            _generate_all_snapshots(
                num_snapshots=num_snapshots + 1,
                upload_config=upload_config,
                cache_dir=cache_dir,
                input_file=input_file,
                generate_task=generate_task,
                progress=progress,
                interval=interval,
            )
        )

        # try to prevent black images and too big files if no kek headers
        path_sizes = [(path, path.stat().st_size) for path in snapshots]
        smallest = min(path_sizes, key=lambda p: p[1])

        snapshots = [
            snap
            for snap, size in path_sizes
            if (snap != smallest[0])
            and (upload_config.kek_headers or size < MAX_SIZE)
        ]

        if not snapshots:
            return images

        upload_task = progress.add_task(
            "[bold magenta]Uploading snapshots[white]",
            total=len(snapshots),
        )

        images = asyncio.run(
            _upload_all_images(
                snapshots,
                upload_task=upload_task,
                progress=progress,
                upload_config=upload_config,
            )
        )

    return images


def get_snapshot_tree(
    uploader: "Uploader",
    input_file: Path | str = "",
    duration: float | int = 0,
) -> "Tree":
    images = Tree("[bold white]Images[not bold]")

    snapshot_links = _get_snapshot_links(
        uploader.upload_config, uploader.cache_dir, input_file, duration
    )

    num_images = len(snapshot_links)
    columns = 0
    for potential_cols in (5, 4, 3, 2):
        if num_images % potential_cols == 0:
            columns = potential_cols
            break

    for num, link in enumerate(snapshot_links, start=1):
        uploader.description += f"| [![]({link})]({link}) "
        if num == columns:
            uploader.description += f"\n{'|---' * columns}|\n"
        elif num % columns == 0:
            uploader.description += "\n"

        images.add(
            f"[not bold cornflower_blue][link={link}]{link}[/link][white /not bold]"
        )

    return images


def rentry_upload(config: SimpleNamespace) -> dict[Any, Any] | None:
    base_url = "https://rentry.co"
    with Session(
        client_identifier="firefox_135", random_tls_extension_order=True
    ) as session:
        max_retries = 5
        retries = 0
        while retries < max_retries:
            res = session.get(
                url=base_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/135.0",
                    "Origin": base_url,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                allow_redirects=True,
            )

            try:
                res = session.post(
                    f"{base_url}/api/new",
                    headers={"Referer": base_url},
                    data={
                        "csrfmiddlewaretoken": session.cookies["csrftoken"],
                        "edit_code": config.edit_code if config.edit_code else "",
                        "text": config.text,
                        "url": "",
                    },
                )

                if res.status_code == 200:
                    try:
                        return res.json()
                    except ValueError:
                        wprint("Rentry upload failed: Invalid JSON response")
                        return {}

            except Exception as e:
                wprint(f"Rentry upload failed: {e} ({retries}/{max_retries})")
                retries += 1
                if retries == max_retries:
                    wprint(f"Rentry upload failed after {max_retries} retries")
                    return {}

        return None
