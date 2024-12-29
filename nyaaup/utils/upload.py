import asyncio
import random
import subprocess
from pathlib import Path

import aiofiles
import httpx
import oxipng
from rich.progress import (BarColumn, MofNCompleteColumn, Progress,
                           TaskProgressColumn, TextColumn, TimeRemainingColumn)
from rich.tree import Tree
from tls_client import Session
from wand.image import Image

from nyaaup.utils.logging import wprint


async def _upload_image(image_path: Path, upload_task, progress, config) -> str:
    async with aiofiles.open(image_path, "rb") as file:
        content = await file.read()
        async with httpx.AsyncClient() as client:
            res = await client.post(
                url="https://kek.sh/api/v1/posts",
                headers=config.upload_config.kek_headers,
                files={"file": content},
            )

            result = res.json()

            progress.update(upload_task, advance=1)

            return f'https://i.kek.sh/{result["filename"]}'


async def _upload_all_images(files, upload_task, progress, config):
    tasks = [_upload_image(file, upload_task, progress, config) for file in files]
    return await asyncio.gather(*tasks)


def snapshot_create_upload(config, input_file: Path, name: str, mediainfo: list) -> Tree:
    images = Tree("[bold white]Images[not bold]")
    num_snapshots = config.upload_config.pic_num + 1
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
            "[bold magenta]Generating snapshots[not bold white]",
            total=config.upload_config.pic_num,
        )

        for x in range(1, num_snapshots):
            snap = Path(f"{config.cache_dir}/{name}_{x}.{config.upload_config.pic_ext}")
            if not snap.exists():
                duration = float(mediainfo[0].get("Duration"))
                interval = duration / (num_snapshots + 1)

                timestamp = (
                    random.randint(round(interval * 10), round(interval * 10 * num_snapshots)) / 10
                    if config.upload_config.random_snapshots
                    else interval * (x + 1)
                )

                subprocess.run(
                    [
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
                        str(snap),
                    ],
                    check=True,
                )

                with Image(filename=snap) as img:
                    img.depth = 8
                    img.save(filename=snap)

                if config.upload_config.pic_ext == "png":
                    oxipng.optimize(snap, level=6)

            snapshots.append(snap)
            progress.update(generate, advance=1)

        if not config.args.skip_upload:
            upload = progress.add_task(
                "[bold magenta]Uploading snapshots[white]",
                total=config.upload_config.pic_num,
            )

            # Filter out large files
            snapshots = [x for x in snapshots if x.stat().st_size < 5 * 1024 * 1024]
            snapshots_link = asyncio.run(_upload_all_images(snapshots, upload, progress, config))
            config.description += "\n\n"
            for link in snapshots_link:
                config.description += f"![]({link})\n"
                images.add(f"[not bold cornflower_blue][link={link}]{link}[/link][white /not bold]")

        return images


def rentry_upload(config) -> dict:
    with Session(client_identifier="firefox_120") as session:
        max_retries = 5
        retries = 0
        while retries < max_retries:
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
                    headers={"Referer": "https://rentry.co"},
                    data={
                        "csrfmiddlewaretoken": session.cookies["csrftoken"],
                        "edit_code": config.edit_code if config.edit_code else "",
                        "text": config.text,
                        "url": "",
                    },
                )

                if res.status_code == 200:
                    return res.json()

            except Exception as e:
                wprint(f"Rentry upload failed: {e} ({retries}/{max_retries})")
                retries += 1
                if retries == max_retries:
                    wprint(f"Rentry upload failed after {max_retries} retries")
                    return {}
