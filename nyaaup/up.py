from pathlib import Path
from types import SimpleNamespace

import cloup
from rich import print as rich_print
from rich.panel import Panel
from rich.traceback import install
from rich.tree import Tree

from nyaaup.utils.logging import eprint, iprint
from nyaaup.utils.upload import snapshot_create_upload
from nyaaup.utils.uploader import Uploader

install(show_locals=True)


@cloup.command()
@cloup.option_group(
    "Upload Tags",
    cloup.option("-u", "--uncensored", is_flag=True, help="Use Uncensored tag in title."),
    cloup.option("-ms", "--multi-subs", is_flag=True, help="Use Multi-Subs tag in title."),
    cloup.option("-da", "--dual-audio", is_flag=True, help="Use Dual-Audio tag in title."),
    cloup.option("-ma", "--multi-audios", is_flag=True, help="Use Multi-Audios tag in title."),
    cloup.option(
        "-a/-na",
        "--auto/--no-auto",
        is_flag=True,
        default=True,
        help="Auto detect Multi-Subs, Multi-Audios or Dual-Audio. (default: True)",
    ),
)
@cloup.option_group(
    "Upload Settings",
    cloup.option(
        "-an", "--anonymous", is_flag=True, default=False, help="Set upload as anonymous."
    ),
    cloup.option("-hi", "--hidden", is_flag=True, default=False, help="Set upload as hidden."),
    cloup.option(
        "-co", "--complete", is_flag=True, default=False, help="Set upload as complete batch."
    ),
    cloup.option("-re", "--remake", is_flag=True, default=False, help="Set upload as remake."),
    cloup.option("-s", "--skip-upload", is_flag=True, default=False, help="Skip torrent upload."),
    cloup.option("-c", "--category", type=str, help="Select a category."),
    cloup.option("-w", "--watch-dir", type=str, metavar="DIR", help="Path of the watch directory."),
)
@cloup.option_group(
    "Content Information",
    cloup.option(
        "-e",
        "--edit-code",
        type=str,
        help="Set edit code for Mediainfo on Rentry.co",
    ),
    cloup.option("-i", "--info", type=str, help="Set information."),
    cloup.option("-n", "--note", type=str, help="Put a note in to the description."),
    cloup.option("-ad", "--advert", type=str, help="Put advert in to the description."),
    cloup.option("-m", "--myanimelist", type=str, metavar="URL", help="MyAnimeList link to use."),
    cloup.option("-t", "--telegram", is_flag=True, default=False, help="Post to telegram."),
    cloup.option(
        "-sm", "--skip-myanimelist", is_flag=True, default=False, help="Skip MyAnimeList."
    ),
)
@cloup.option_group(
    "Media Settings",
    cloup.option(
        "-p",
        "--pictures-number",
        type=int,
        default=3,
        metavar="EXTENSION",
        help="Number of pictures to use (default: 3).",
    ),
    cloup.option(
        "-pe",
        "--picture-extension",
        type=str,
        default="png",
        metavar="NUM",
        help="Extension of the pictures.",
    ),
    cloup.option(
        "-M",
        "--no-mediainfo",
        is_flag=True,
        default=False,
        help="Do not attach Mediainfo to the torrent.",
    ),
    cloup.option(
        "-o/-no",
        "--overwrite/--no-overwrite",
        is_flag=True,
        default=True,
        help="Create torrent file even if exists. (default: True)",
    ),
)
@cloup.option("-ch", "--category-help", is_flag=True, help="Print available categories.")
@cloup.argument("path", type=Path, nargs=-1, required=False)
@cloup.pass_context
def up(ctx, **kwargs):
    """Upload torrents to Nyaa"""
    uploader = Uploader(ctx, SimpleNamespace(**kwargs))

    for file_path in uploader.args.path:
        display_info = Tree("[bold white]Information[not bold]")

        uploader.description = ""
        uploader.file = ""
        uploader.mediainfo = []

        name_plus: list[str] = []
        dual_audio: bool = False
        multi_audio: bool = False
        multi_sub: bool = False

        name: str = uploader.get_file_name(file_path)
        style: str = "red"
        title: str = "Upload failed"

        if result := uploader.process_file(file_path, display_info):
            display_info = result.display_info
            if uploader.args.auto:
                dual_audio = result.audio_len == 2
                multi_audio = result.audio_len > 2
                multi_sub = result.sub_len > 1

            if uploader.upload_config.pic_num > 0:
                uploader.description += "\n\n---\n\n"

            if uploader.is_anime_category and not uploader.args.skip_myanimelist:
                name_plus.extend(
                    uploader.process_mal_info(name, uploader.upload_config.info_form_config)
                )
                if uploader.upload_config.info:
                    display_info.add(
                        f"[bold white]MAL link: [cornflower_blue not bold]{uploader.upload_config.info}[white]"
                    )

            if dual_audio:
                name_plus.append("Dual-Audio")
            elif multi_audio:
                name_plus.append("Multi-Audio")
            if multi_sub:
                name_plus.append("Multi-Subs")
            if uploader.args.uncensored:
                name_plus.append("Uncensored")

            display_name = uploader.format_display_name(name, name_plus)

            for provider in uploader.providers:
                ok_cookies = uploader.check_cookies(provider)
                if uploader.upload_config.pic_num > 0 and not ok_cookies:
                    if images := snapshot_create_upload(
                        config=uploader, input_file=uploader.file, mediainfo=uploader.mediainfo
                    ):
                        display_info.add(images)

                iprint("Uploading to Nyaa...")

                upload_result = uploader.try_upload_with_retries(display_name, name, provider)

                if upload_result:
                    if (
                        uploader.upload_config.telegram_enabled
                        and not uploader.upload_config.hidden
                    ):
                        uploader.send_notification(upload_result)
                    watch_dir = uploader.args.watch_dir or uploader.upload_config.watch_dir

                    if watch_dir:
                        try:
                            watch_dir = Path(watch_dir)
                        except Exception as e:
                            eprint(f"Failed to load watch directory: {e}")

                        if uploader.copy_to_watch_dir(file_path, watch_dir):
                            display_info.add(
                                "[bold white]Successfully copied to watch directory[white]"
                            )
                        else:
                            display_info.add("[bold white]Failed to copy to watch directory[white]")

                    display_info = uploader.display_success(display_info, upload_result, provider)

                    if ok_cookies and uploader.upload_config.pic_num > 0:
                        display_info = uploader.handle_image_upload(
                            upload_result,
                            display_info,
                            provider,
                        )

                    style = "bold green"
                    title = "Torrent successfully uploaded!"
                else:
                    style = "yellow"
                    title = "Upload completed with warnings"

        print("")
        rich_print(Panel.fit(display_info, title=title, border_style=style))
