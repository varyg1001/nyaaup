import asyncio
import random
from pathlib import Path
from types import SimpleNamespace

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

            return f"https://i.kek.sh/{result['filename']}"


async def _upload_all_images(files, upload_task, progress, config):
    tasks = [_upload_image(file, upload_task, progress, config) for file in files]
    return await asyncio.gather(*tasks)


async def _generate_snapshot(
    num: int, config, input_file: Path, generate_task, progress, interval, num_snapshots
) -> Path:
    out_path = Path(f"{config.cache_dir}/snapshot_{num}.{config.upload_config.pic_ext}")
    if not out_path.exists():
        timestamp = (
            random.randint(round(interval * 10), round(interval * 10 * num_snapshots)) / 10
            if config.upload_config.random_snapshots
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
            if config.upload_config.pic_ext == "png":
                oxipng.optimize(out_path, level=6)

        await loop.run_in_executor(None, process_image)

    progress.update(generate_task, advance=1)

    return out_path


async def _generate_all_snapshots(
    num_snapshots: int, config, input_file: Path, generate_task, progress, interval
) -> list[Path]:
    tasks = [
        _generate_snapshot(x, config, input_file, generate_task, progress, interval, num_snapshots)
        for x in range(1, num_snapshots)
    ]
    return await asyncio.gather(*tasks)


def snapshot_create_upload(config: SimpleNamespace, input_file: Path, mediainfo: list) -> "Tree":
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
        generate_task = progress.add_task(
            "[bold magenta]Generating snapshots[not bold white]",
            total=config.upload_config.pic_num,
        )

        duration = float(mediainfo[0].get("Duration"))
        interval = duration / (num_snapshots + 1)

        snapshots = asyncio.run(
            _generate_all_snapshots(
                num_snapshots, config, input_file, generate_task, progress, interval
            )
        )

        if not config.args.skip_upload:
            upload_task = progress.add_task(
                "[bold magenta]Uploading snapshots[white]",
                total=config.upload_config.pic_num,
            )

            snapshots = [snap for snap in snapshots if snap.stat().st_size < 5 * 1024 * 1024]
            snapshots_link = asyncio.run(
                _upload_all_images(snapshots, upload_task, progress, config)
            )
            for link in snapshots_link:
                config.description += f"![]({link})\n"
                images.add(f"[not bold cornflower_blue][link={link}]{link}[/link][white /not bold]")

    return images


def rentry_upload(config: SimpleNamespace) -> dict:
    base_url = "https://rentry.co"
    with Session(client_identifier="firefox_120") as session:
        max_retries = 5
        retries = 0
        while retries < max_retries:
            res = session.get(
                url=base_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
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
                    return res.json()

            except Exception as e:
                wprint(f"Rentry upload failed: {e} ({retries}/{max_retries})")
                retries += 1
                if retries == max_retries:
                    wprint(f"Rentry upload failed after {max_retries} retries")
                    return {}
