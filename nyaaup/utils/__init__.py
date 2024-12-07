from difflib import SequenceMatcher

import cloup
import httpx
from mal import Anime, AnimeSearch
from rich.console import Console
from rich.tree import Tree

from nyaaup.utils.collections import first_or_none


class DefaultCommandGroup(cloup.Group):
    def parse_args(self, ctx, args):
        first_arg = first_or_none(x for x in args if not x.startswith("-"))
        if first_arg not in self.list_commands(ctx):
            args.insert(0, "up")
        return super().parse_args(ctx, args)


def similar(x: str, y: str) -> float:
    return SequenceMatcher(None, x, y).ratio()


def get_mal_link(myanimelist: str, name_to_mal: str) -> Anime | None:
    console = Console()

    if myanimelist:
        with console.status("[bold magenta]Getting MyAnimeList info from input link..."):
            malid = int(str(myanimelist).split("/")[4])
            return Anime(malid)

    with console.status("[bold magenta]Searching in MyAnimeList database..."):
        data = AnimeSearch(name_to_mal).results[:10]

        for result in data:
            anime = Anime(result.mal_id)
            name_in = (name_to_mal or "").casefold()
            name_en = (anime.title_english or "").casefold()
            name_ori = (anime.title or "").casefold()

            if (similar(name_en, name_in) >= 0.75) or (similar(name_ori, name_in) >= 0.75):
                return anime

        return Anime(data[0].mal_id) if data else None


def cat_help() -> None:
    categories = Tree("[chartreuse2]Available categories:[white /not bold]")
    cats = [
        "Anime - English-translated",
        "Anime - Non-English-translated",
        "Anime - Raw",
        "Live Action - English-translated",
        "Live Action - Non-English-translated",
        "Live Action - Raw",
        "Anime - Anime Music Video",
    ]

    for num, cat in enumerate(cats, start=1):
        categories.add(f"[{num}] [cornflower_blue not bold]{cat}[white /not bold]")

    Console().print(categories)


def tgpost(config, message: str | None = None) -> None:
    if message and config.tg_token and config.tg_id:
        with httpx.Client(transport=httpx.HTTPTransport(retries=5)) as client:
            client.post(
                url=f"https://api.telegram.org/bot{config.tg_token}/sendMessage",
                params={
                    "text": message,
                    "chat_id": config.tg_id,
                    "parse_mode": "html",
                    "disable_web_page_preview": True,
                },
            )
