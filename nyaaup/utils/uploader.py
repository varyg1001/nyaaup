import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import httpx
from mal import Anime
from pymediainfo import MediaInfo
from rich.console import Console
from rich.traceback import install
from rich.tree import Tree

from nyaaup.utils import cat_help, get_mal_link, tg_post
from nyaaup.utils.logging import eprint, wprint
from nyaaup.utils.mediainfo import get_description, parse_mediainfo
from nyaaup.utils.torrent import create_torrent
from nyaaup.utils.upload import rentry_upload, snapshot_create_upload
from nyaaup.utils.userconfig import Config

install(show_locals=True)


@dataclass
class UploadConfig:
    category: str
    anonymous: bool = False
    hidden: bool = False
    complete: bool = False
    remake: bool = False
    trusted: bool = False
    mediainfo_enabled: bool = True
    telegram_enabled: bool = False
    random_snapshots: bool = False
    pic_num: int = 3
    pic_ext: str = "png"
    edit_code: str | None = None
    text: str | None = None
    tg_token: str | None = None
    tg_id: str | None = None
    kek_headers: dict[str, str] | None = None
    info_form_config: bool = False
    info: str = ""


@dataclass
class Provider:
    name: str
    domain: str
    proxy: str
    credentials: SimpleNamespace


@dataclass
class UploadResult:
    url: str
    id: str
    download_url: str
    name: str


@dataclass
class ProcessResult:
    video_info: str
    audio_info: list
    sub_info: list
    display_info: Tree


class NyaaUploader:
    def __init__(self, ctx, args):
        self.ctx = ctx
        self.args = args
        self.announces = []
        self.add_pub_trackers = False

        self.console = Console()
        self.mediainfo = []
        self.description = ""
        self.file = ""

        self._validate_inputs()
        self._setup_config()

    def _validate_inputs(self):
        if not self.args.path:
            eprint("No input!\n")
            print(self.ctx.get_help())
            sys.exit(1)

        if not self.args.category:
            eprint("No selected category!\n")
            cat_help(self.console)
            sys.exit(1)

        if self.args.category_help:
            cat_help(self.console)
            sys.exit(1)

    def _setup_config(self) -> None:
        self.config = Config()
        self._validate_config()
        if not (pref := self.config.get("preferences")):
            eprint("No preferences in config!", True)

        self.upload_config = UploadConfig(
            category=self._get_category(self.args.category),
            anonymous="anonymous" if self.args.anonymous else None,
            hidden="hidden" if self.args.hidden else None,
            complete="complete" if self.args.complete else None,
            remake="remake" if self.args.remake else None,
            trusted="trusted" if self.config.get("trusted") else None,
            mediainfo_enabled=not self.args.no_mediainfo and pref.get("mediainfo", True),
            telegram_enabled=pref.get("telegram", False),
            random_snapshots=pref.get("random_snapshots", False),
            pic_num=self.args.pictures_number,
            pic_ext=self.args.picture_extension,
            edit_code=self.args.edit_code or pref.get("edit_code"),
            tg_token=pref.get("token"),
            tg_id=pref.get("id"),
            info_form_config=(
                False if (pref.get("info", "").lower() == "mal") or not pref.get("info") else True
            ),
        )

        self.providers = self._setup_providers()
        self.headers = self._get_default_headers()

        if key := pref.get("keks_key"):
            self.upload_config.kek_headers = {"x-kek-auth": key, **self.headers}

    def _setup_providers(self) -> list[Provider]:
        providers = []

        for p in self.config.get("providers", []):
            if cred := p.get("credentials"):
                self.config.load_credentials(cred)
            else:
                eprint("No credentials in config!", True)

            if not (domain := p.get("domain")):
                eprint("No domain in config!", True)

            provider = Provider(
                name=p.get("name", ""),
                domain=domain,
                proxy=p.get("proxy", ""),
                credentials=self.config.credentials,
            )

            if p.get("add_pub_trackers", False):
                self.add_pub_trackers = True

            if announces := p.get("announces", []):
                self.announces.extend(list(announces))

            providers.append(provider)

        return providers

    def _get_default_headers(self) -> dict[str, str]:
        return {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "dnt": "1",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "upgrade-insecure-requests": "1",
        }

    def process_file(self, file_path: Path, display_info: Tree) -> ProcessResult | None:
        if not file_path.exists():
            eprint(f"Input path not found: {file_path}", True)

        self.file = (
            file_path
            if file_path.is_file()
            else Path(sorted([*file_path.glob("*.mkv"), *file_path.glob("*.mp4")])[0])
        )
        name = str(file_path.name).removesuffix(".mkv").removesuffix(".mp4")

        self.cache_dir = Path(f"{self.config.dirs.user_cache_path}/{name}_files")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        with self.console.status("[bold magenta]Parsing file...") as _:
            parse_mediainfo(self, self.file)

        if not self.mediainfo:
            return None

        if not create_torrent(self, name, file_path, self.args.overwrite):
            return None

        video_info, audio_info, sub_info = get_description(self.mediainfo)
        self._set_description(video_info, audio_info, sub_info, self.mediainfo)

        if self.upload_config.mediainfo_enabled:
            self.upload_config.text = MediaInfo.parse(self.file, output="", full=False).replace(
                str(self.file), str(self.file.name)
            )
            if mediainfo_upload := self._upload_mediainfo():
                url = mediainfo_upload["url"]
                display_info = self._add_media_info_display(
                    display_info, url, mediainfo_upload["edit_code"]
                )
                self.description += f"\n[Full MediaInfo]({url})"

        return ProcessResult(
            video_info=video_info,
            audio_info=audio_info,
            sub_info=sub_info,
            display_info=display_info,
        )

    def _set_description(
        self,
        video_info: str,
        audio_info: list[str],
        sub_info: list[str],
        mediainfo: list,
    ) -> None:
        if note := (self.args.note or self.config.get("preferences", {}).get("note")):
            self.description += f"{note}\n\n---\n\n"

        chapter_str = ["No", "Yes"][bool(mediainfo[0].get("MenuCount", False))]
        duration_str = mediainfo[0].get("Duration_String3", "?")

        self.description += (
            f"`Tech Specs:`\n"
            f"* `Video:` {video_info}\n"
            f"* `Audios ({len(audio_info)}):` {' │ '.join(audio_info)}\n"
            f"* `Subtitles ({len(sub_info)}):` {' │ '.join(sub_info) if sub_info else '**N/A**'}\n"
            f"* `Chapters:` **{chapter_str}**\n"
            f"* `Duration:` **~{duration_str}**\n"
        )

    def _upload_mediainfo(self) -> dict | None:
        try:
            return rentry_upload(self.upload_config)
        except Exception as e:
            wprint(f"Failed to upload mediainfo: {e}")

            return None

    def try_upload_with_retries(
        self, display_name: str, name: str, provider: Provider, max_retries: int = 3
    ) -> UploadResult | None:
        torrent_path = self.cache_dir / f"{name}.torrent"
        with open(torrent_path, "rb") as f:
            torrent_data = f.read()

        for attempt in range(max_retries):
            try:
                if result := self._try_upload(provider, torrent_data, name, display_name):
                    return result
            except Exception as e:
                delay = 2 ** (attempt - 1)
                wprint(f"Attempt {attempt + 1} failed for {provider.name}: {e}")
                if attempt < max_retries:
                    eprint("All upload attempts failed", True)
                time.sleep(delay)

        return None

    def _try_upload(
        self, provider: Provider, torrent_data: bytes, name: str, display_name: str
    ) -> UploadResult | None:
        try:
            response = httpx.post(
                f"{provider.domain}/api/v2/upload",
                files={
                    "torrent": (
                        f"{name}.torrent",
                        torrent_data,
                        "application/x-bittorrent",
                    ),
                    "torrent_data": (
                        None,
                        json.dumps(
                            {
                                "name": display_name,
                                "category": self.upload_config.category,
                                "description": self.description,
                                "anonymous": self.upload_config.anonymous,
                                "hidden": self.upload_config.hidden,
                                "complete": self.upload_config.complete,
                                "remake": self.upload_config.remake,
                                "trusted": self.upload_config.trusted,
                                "information": self.upload_config.info,
                            }
                        ),
                    ),
                },
                auth=(provider.credentials.username, provider.credentials.password),
                headers=self.headers,
                proxies={"all://": provider.proxy} if provider.proxy else None,
            )

            result = response.json()
            if errors := result.get("errors"):
                self._handle_upload_errors(errors)
                raise Exception("Upload failed")

            return UploadResult(
                url=result["url"],
                id=result["id"],
                download_url=self._get_download_url(result["url"], result["id"]),
                name=display_name,
            )

        except Exception as e:
            eprint(f"Upload failed: {e}")
            return None

    def _handle_upload_errors(self, errors: dict) -> None:
        if isinstance(errors, str):
            eprint(errors)
        else:
            info = next(iter(errors))
            eprint(f"{info} error: {errors[info][0]}", True)

    def _edit_torrent(
        self,
        provider: Provider,
        torrent_id: str,
        display_name: str,
        information: str,
    ) -> bool:
        try:
            response = httpx.post(
                f"{provider.domain}/view/{torrent_id}/edit",
                files={
                    "display_name": (None, display_name),
                    **({"is_anonymous": (None, "y")} if self.upload_config.anonymous else {}),
                    **({"is_remake": (None, "y")} if self.upload_config.remake else {}),
                    **({"is_complete": (None, "y")} if self.upload_config.complete else {}),
                    **({"is_hidden": (None, "y")} if self.upload_config.hidden else {}),
                    "category": (None, self.upload_config.category),
                    "information": (None, information),
                    "description": (None, self.description),
                    "submit": (None, "Save Changes"),
                },
                cookies=self.config.cookies,
                headers={
                    **self.headers,
                    "origin": provider.domain,
                    "referer": f"{provider.domain}/view/{torrent_id}/edit",
                },
            )
            return response.status_code == 302
        except Exception as e:
            eprint(f"Failed to edit torrent: {e}")
            return False

    def _get_download_url(self, page_url: str, torrent_id: str) -> str:
        return page_url.replace(f"view/{torrent_id}", f"download/{torrent_id}.torrent")

    def send_notification(self, result: UploadResult) -> None:
        if self.upload_config.tg_token and self.upload_config.tg_id:
            message = (
                f"\n{result.name}\n\n"
                f"Nyaa link: {result.url}\n"
                f'<a href="{result.download_url}">Torrent file</a>'
            )
            tg_post(self, message)

    def _get_category(self, category: str) -> str:
        return {
            "Anime - Anime Music Video": "1_1",
            "7": "1_1",
            "Anime - English-translated": "1_2",
            "1": "1_2",
            "Anime - Non-English-translated": "1_3",
            "2": "1_3",
            "Anime - Raw": "1_4",
            "3": "1_4",
            "Live Action - English-Translated": "4_1",
            "4": "4_1",
            "Live Action - Non-English-translated": "4_1",
            "5": "4_1",
            "Live Action - Raw": "4_4",
            "6": "4_4",
        }.get(category, category)

    def detect_audio_subs(
        self, audio_info: list[str], sub_info: list[str]
    ) -> tuple[bool, bool, bool]:
        audio_len = len(audio_info)
        sub_len = len(sub_info)

        if self.config.get("preferences", {}).get("real_length", False):
            if sub_len > 1:
                try:
                    sub_len = len(
                        {x.split("**")[1] for x in sub_info if "**" in x and len(x.split("**")) > 1}
                    )
                except (IndexError, Exception) as e:
                    wprint(f"Error processing subtitle info: {e}")
                    sub_len = len(sub_info)

            if audio_len > 1:
                try:
                    audio_len = len(
                        {
                            x.split("**")[1]
                            for x in audio_info
                            if "**" in x and len(x.split("**")) > 1
                        }
                    )
                except (IndexError, Exception) as e:
                    wprint(f"Error processing audio info: {e}")
                    audio_len = len(audio_info)

        return (
            audio_len == 2,  # dual_audio
            audio_len > 2,  # multi_audio
            sub_len > 1,  # multi_sub
        )

    def format_display_name(self, name: str, name_plus: list[str]) -> str:
        name_nyaa = name.replace(".", " ")
        if channel := re.search(r"[A-Z]{3}[2|5|7] [0|1]", name_nyaa):
            c = channel[0]
            name_nyaa = name_nyaa.replace(c, c.replace(" ", "."))

        return f'{name_nyaa} ({", ".join(name_plus)})' if name_plus else name_nyaa

    def _add_media_info_display(self, display_info: Tree, mediainfo_url: str, edit_code: str):
        medlink = Tree(
            f"[bold white]MediaInfo link: [cornflower_blue not bold][link={mediainfo_url}]{mediainfo_url}[/link][white]"
        )
        medlink.add(f"[bold white]Edit code: [cornflower_blue not bold]{edit_code}[white]")
        display_info.add(medlink)

        return display_info

    def check_cookies(self, provider: Provider) -> bool:
        if self.config.cookies:
            try:
                res = httpx.get(
                    f"{provider.domain}/profile",
                    cookies=self.config.cookies,
                    headers=self.headers,
                    proxy=provider.proxy,
                )
                return res.status_code == 200
            except Exception:
                wprint("Failed to verify cookies")
                return False

        return False

    def _validate_config(self) -> None:
        required = ["preferences", "providers"]
        for key in required:
            if key not in self.config:
                eprint(f"Missing {key} in config!", True)

        pref = self.config["preferences"]
        if not pref.get("mediainfo") and not self.args.no_mediainfo:
            wprint("MediaInfo disabled in config")

    def handle_image_upload(
        self,
        result: UploadResult,
        display_info: Tree,
        file_path: Path,
        provider: Provider,
    ):
        # try:
        images = snapshot_create_upload(self, file_path, result.name, self.mediainfo)
        if images:
            display_info.add(images)
            for _ in range(5):
                if self._edit_torrent(
                    provider,
                    result.id,
                    result.name,
                    result.url,
                ):
                    return display_info
                time.sleep(5)
            wprint("Failed to add images to torrent after retries")
        # except Exception as e:
        #    wprint(f"Image upload failed: {e}")

        return display_info

    def display_success(self, display_info: Tree, result: UploadResult, provider):
        info = Tree(f"[bold white]Links for {provider.name}[not bold]")
        info.add(
            f"[bold white]Page link: [cornflower_blue not bold][link={result.url}]{result.url}[/link][white]"
        )
        info.add(
            f"[bold white]Download link: [cornflower_blue not bold]{result.download_url}[white]"
        )

        display_info.add(info)

        return display_info

    @property
    def is_anime_category(self) -> bool:
        return self.upload_config.category in {"1_1", "1_2", "1_3", "1_4"}

    @property
    def is_non_english_category(self) -> bool:
        return self.upload_config.category in {"1_3", "1_4"}

    def _get_mal_titles(self, mal_data: Anime) -> list[str]:
        titles = []

        if hasattr(self, "name_to_mal"):
            if (
                self.is_non_english_category
                and mal_data.title_english
                and mal_data.title_english.casefold() not in self.name_to_mal.casefold()
            ):
                titles.append(mal_data.title_english)
            elif mal_data.title and mal_data.title.casefold() not in self.name_to_mal.casefold():
                titles.append(mal_data.title)

        return titles

    def process_mal_info(self, name: str, info_from_config: bool) -> tuple[str, list[str]]:
        """Process MAL info and return information and name additions"""
        name_plus = []

        if not info_from_config and self.is_anime_category and not self.args.skip_myanimelist:
            name_to_mal = re.sub(r"[\.|\-]S\d+.*", "", name)
            if name_to_mal == name:
                name_to_mal = re.sub(r"[\.|\-]\d{4}\..*", "", name)
            name_to_mal = name_to_mal.replace(".", " ")

            self.name_to_mal = name_to_mal

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    mal_data: Anime = get_mal_link(self.args.myanimelist, name_to_mal, self.console)
                except Exception as e:
                    delay = 2 ** (attempt - 1)
                    wprint(f"Attempt {attempt + 1} failed for: {e}")
                    if attempt < max_retries:
                        eprint("All myanimelist attempts failed", True)
                    time.sleep(delay)

            if self.args.myanimelist:
                self.upload_config.info = self.args.myanimelist
            elif mal_data and hasattr(mal_data, "url"):
                try:
                    self.upload_config.info = f"{'/'.join(mal_data.url.split('/')[:-1])}/"
                except Exception as e:
                    wprint(f"Failed to process MAL URL: {e}")

            if mal_data:
                try:
                    name_plus.extend(self._get_mal_titles(mal_data))
                except Exception as e:
                    wprint(f"Failed to get MAL titles: {e}")

        return name_plus

    def get_file_name(self, file_path: Path) -> str:
        if file_path.is_file():
            return str(file_path.name).removesuffix(".mkv").removesuffix(".mp4")

        return file_path.name