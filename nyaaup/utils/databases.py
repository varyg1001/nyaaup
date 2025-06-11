import re
import time

import httpx
from mal import Anime, AnimeSearch
from rich.console import Console

from nyaaup.utils import similar
from nyaaup.utils.collections import first, first_or_none
from nyaaup.utils.logging import eprint, wprint
from nyaaup.utils.uploader import Uploader


def extract_name_from_filename(file_name: str) -> str:
    name = re.sub(r"[\.|\-]S\d+.*", "", file_name)
    if name == file_name:
        name = re.sub(r"[\.|\-]\d{4}\..*", "", file_name)
    name = name.replace(".", " ")[:100]

    return name


def get_anilist_link(anilist_url: str, search_name: str) -> dict[str, str | int]:
    if anilist_url:
        json_data = {
            "query": """
                query ($id: Int) {
                    Media(id: $id, type: ANIME) {
                        idMal
                        siteUrl
                        title {
                            romaji
                            english
                        }
                    }
                }
            """,
            "variables": {"id": str(anilist_url).split("/")[4]},
        }
    else:
        json_data = {
            "query": """
                query ($search: String) {
                    Page(perPage: 10) {
                        media(search: $search, type: ANIME) {
                        idMal
                        siteUrl
                        title {
                            romaji
                            english
                        }
                        }
                    }
                }
            """,
            "variables": {"search": search_name},
        }

    with httpx.Client(transport=httpx.HTTPTransport(retries=5)) as client:
        res = client.post(
            url="https://graphql.anilist.co",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=json_data,
        ).json()

    if error := first_or_none(res.get("errors", [])):
        wprint(f"Anilist error: {error.get('message')}")
        return {}

    if anilist_url:
        return res.get("data", {}).get("media")
    else:
        if data := res.get("data", {}).get("Page", {}).get("media", []):
            for result in data:
                name_in = (search_name or "").casefold()
                name_en = (result.get("title", {}).get("english") or "").casefold()
                name_ori = (result.get("title", {}).get("romaji") or "").casefold()

                if (similar(name_en, name_in) >= 0.75) or (
                    similar(name_ori, name_in) >= 0.75
                ):
                    return result

    return {}


def get_mal_link(mal_url: str, search_name: str, console: Console) -> Anime | None:
    if mal_url:
        with console.status("[bold magenta]Getting MyAnimeList info from input link..."):
            mal_id = int(str(mal_url).split("/")[4])

            return Anime(mal_id)

    with console.status("[bold magenta]Searching in MyAnimeList database..."):
        if data := AnimeSearch(search_name).results:
            data = data[:10]

            for result in data:
                anime = Anime(result.mal_id)
                name_in = (search_name or "").casefold()
                name_en = (anime.title_english or "").casefold()
                name_ori = (anime.title or "").casefold()
                name_syn = ""
                if anime.title_synonyms:
                    name_syn = (anime.title_synonyms[0] or "").casefold()

                if (
                    (similar(name_en, name_in) >= 0.75)
                    or (similar(name_ori, name_in) >= 0.75)
                    or (similar(name_syn, name_in) >= 0.75)
                ):
                    return anime

            data_likely = first(
                sorted(data, key=lambda x: similar(x.title, search_name), reverse=True)
            )

            return Anime(data_likely.mal_id) if data else None

    return None


def _get_anilist_title(
    uploader: Uploader, anilist_data: dict, search_name: str
) -> str | None:
    title: dict[str, str] = anilist_data.get("title", {})
    if uploader.is_non_english_category and title.get("english"):
        if title.get("english").casefold() not in search_name.casefold():
            return title.get("english")
        else:
            return ""
    elif title.get("romaji"):
        if title.get("romaji").casefold() not in search_name.casefold():
            if len(title.get("romaji")) > 85:
                return title.get("romaji")[80:]
            else:
                return title.get("romaji")
        else:
            return ""

    return None


def _get_mal_title(uploader: Uploader, mal_data: Anime, search_name: str) -> str:
    if (
        uploader.is_non_english_category
        and mal_data.title_english
        and mal_data.title_english.casefold() not in search_name.casefold()
    ):
        return mal_data.title_english
    elif mal_data.title and mal_data.title.casefold() not in search_name.casefold():
        if len(mal_data.title) > 85:
            if (
                mal_data.title_synonyms
                and len(mal_data.title_synonyms[0]) < 85
                and mal_data.title_synonyms[0].casefold() not in search_name.casefold()
            ):
                return mal_data.title_synonyms[0]
            else:
                return mal_data.title[80:]
        else:
            return mal_data.title

    return ""


def process_mal_info(uploader: Uploader, name: str) -> str:
    """Process MAL info and return information and name additions"""
    search_name: str = extract_name_from_filename(name)

    max_retries = 3
    mal_data: Anime | None = None
    for attempt in range(max_retries):
        try:
            mal_data = get_mal_link(uploader.args.link, search_name, uploader.console)
        except Exception as e:
            delay = 2 ** (attempt - 1)
            wprint(f"Attempt {attempt + 1} failed for: {e}")
            if attempt == max_retries:
                eprint("All MyAnimeList attempts failed")
                return ""

            time.sleep(delay)

    if uploader.args.link:
        uploader.upload_config.info = uploader.args.link
    elif mal_data and hasattr(mal_data, "url"):
        try:
            uploader.upload_config.info = f"{'/'.join(mal_data.url.split('/')[:-1])}/"
        except Exception as e:
            wprint(f"Failed to process MAL URL: {e}")

    if mal_data:
        try:
            return _get_mal_title(uploader, mal_data, search_name)
        except Exception as e:
            wprint(f"Failed to get MAL title: {e}")

    return ""


def process_anilist_info(uploader: Uploader, name: str) -> str:
    """Process AniList info and return information and name additions"""
    search_name: str = extract_name_from_filename(name)

    anilist_data = get_anilist_link(uploader.args.link, search_name)

    if uploader.args.link:
        uploader.upload_config.info = uploader.args.link
    elif anilist_data:
        try:
            uploader.upload_config.info = anilist_data.get("siteUrl")
        except Exception as e:
            wprint(f"Failed to process AniList URL: {e}")

    if anilist_data:
        title = _get_anilist_title(uploader, anilist_data, search_name)
        if title is not None:
            return title
        else:
            wprint("Failed to get AniList title")
    else:
        wprint("Failed to get AniList data")

    return ""
