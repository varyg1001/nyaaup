from difflib import SequenceMatcher
from enum import Enum

import cloup
import httpx
import humanize
from rich.console import Console
from rich.progress import TimeRemainingColumn
from rich.text import Text
from rich.tree import Tree

from nyaaup.utils.collections import first_or_none
from nyaaup.utils.logging import wprint


class DefaultCommandGroup(cloup.Group):
    def parse_args(self, ctx, args):
        if not any(x in args for x in ["-h", "-v", "--help", "--version"]):
            first_arg = first_or_none(x for x in args if not x.startswith("-"))
            if first_arg not in self.list_commands(ctx):
                args.insert(0, "up")

        return super().parse_args(ctx, args)


class CustomTransferSpeedColumn(TimeRemainingColumn):
    def render(self, task):
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("--", style="progress.data.speed")
        return Text(
            f"{humanize.naturalsize(int(speed), binary=True)}/s",
            style="progress.data.speed",
        )


class Category(Enum):
    ANIME_ENGLISH = ("1_2", "Anime - English-translated", "1")
    ANIME_NON_ENGLISH = ("1_3", "Anime - Non-English-translated", "2")
    ANIME_RAW = ("1_4", "Anime - Raw", "3")
    LIVE_ENGLISH = ("4_1", "Live Action - English-Translated", "4")
    LIVE_NON_ENGLISH = ("4_3", "Live Action - Non-English-translated", "5")
    LIVE_RAW = ("4_4", "Live Action - Raw", "6")
    ANIME_MUSIC_VIDEO = ("1_1", "Anime - Anime Music Video", "7")

    def __init__(self, id: str, display_name: str, numeric_id: str):
        self.id = id
        self.display_name = display_name
        self.numeric_id = numeric_id


def similar(x: str, y: str) -> float:
    return SequenceMatcher(None, x, y).ratio()


def cat_help(console: Console) -> None:
    categories = Tree("[chartreuse2]Available categories:[white /not bold]")

    for cat in Category:
        categories.add(
            f"[{cat.numeric_id}] [cornflower_blue not bold]{cat.display_name}[white /not bold]"
        )

    console.print(categories)


def tg_post(config, message: str | None = None) -> None:
    if message and config.upload_config.tg_token and config.upload_config.tg_id:
        with httpx.Client(transport=httpx.HTTPTransport(retries=5)) as client:
            client.post(
                url=f"https://api.telegram.org/bot{config.upload_config.tg_token}/sendMessage",
                params={
                    "text": message,
                    "chat_id": config.upload_config.tg_id,
                    "parse_mode": "html",
                    "disable_web_page_preview": True,
                },
            )
    else:
        wprint("Telegram token or chat id not set.")
