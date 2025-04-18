from difflib import SequenceMatcher
from enum import Enum

import cloup
import httpx
import humanize
from mal import Anime, AnimeSearch
from rich.console import Console
from rich.progress import TimeRemainingColumn
from rich.text import Text
from rich.tree import Tree

from nyaaup.utils.collections import first, first_or_none
from nyaaup.utils.logging import wprint


class DefaultCommandGroup(cloup.Group):
    def parse_args(self, ctx, args):
        if "-h" not in args and "--help" not in args:
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
    ANIME_MUSIC_VIDEO = ("1_1", "Anime - Anime Music Video", "7")
    ANIME_ENGLISH = ("1_2", "Anime - English-translated", "1")
    ANIME_NON_ENGLISH = ("1_3", "Anime - Non-English-translated", "2")
    ANIME_RAW = ("1_4", "Anime - Raw", "3")
    LIVE_ENGLISH = ("4_1", "Live Action - English-Translated", "4")
    LIVE_NON_ENGLISH = ("4_3", "Live Action - Non-English-translated", "5")
    LIVE_RAW = ("4_4", "Live Action - Raw", "6")

    def __init__(self, id: str, display_name: str, numeric_id: str):
        self.id = id
        self.display_name = display_name
        self.numeric_id = numeric_id


def similar(x: str, y: str) -> float:
    return SequenceMatcher(None, x, y).ratio()


def get_mal_link(mal_url: str, name_to_mal: str, console: Console) -> Anime | None:
    if mal_url:
        with console.status("[bold magenta]Getting MyAnimeList info from input link..."):
            mal_id = int(str(mal_url).split("/")[4])

            return Anime(mal_id)

    with console.status("[bold magenta]Searching in MyAnimeList database..."):
        if data := AnimeSearch(name_to_mal).results:
            data = data[:10]

            for result in data:
                anime = Anime(result.mal_id)
                name_in = (name_to_mal or "").casefold()
                name_en = (anime.title_english or "").casefold()
                name_ori = (anime.title or "").casefold()

                if (similar(name_en, name_in) >= 0.75) or (similar(name_ori, name_in) >= 0.75):
                    return anime

            data_likely = first(
                sorted(data, key=lambda x: similar(x.title, name_to_mal), reverse=True)
            )

            return Anime(data_likely.mal_id) if data else None

    return None


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
