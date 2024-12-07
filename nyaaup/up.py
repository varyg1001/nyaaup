from pathlib import Path
from types import SimpleNamespace

import cloup
from rich import print as rich_print
from rich.panel import Panel
from rich.traceback import install
from rich.tree import Tree

from nyaaup.utils.logging import iprint
from nyaaup.utils.upload import snapshot
from nyaaup.utils.uploader import NyaaUploader

install(show_locals=True)


@cloup.command()
@cloup.option_group(
    "Upload Tags",
    cloup.option("-ms", "--multi-subs", is_flag=True, help="Add Multi Subs tag to title."),
    cloup.option("-da", "--dual-audios", is_flag=True, help="Add Dual audios tag to title."),
    cloup.option("-ma", "--multi-audios", is_flag=True, help="Add Multi audios tag to title."),
    cloup.option(
        "-a",
        "--auto",
        is_flag=True,
        help="Detect multi subs, multi audios and dual audios.",
    ),
)
@cloup.option_group(
    "Upload Settings",
    cloup.option("-an", "--anonymous", is_flag=True, help="Upload torrent as anonymous."),
    cloup.option("-hi", "--hidden", is_flag=True, help="Upload the torrent as hidden."),
    cloup.option("-co", "--complete", is_flag=True, help="If the torrnet is a complete batch."),
    cloup.option("-re", "--remake", is_flag=True, help="If the torrnet is a remake."),
    cloup.option("-s", "--skip-upload", is_flag=True, help="Skip torrent upload."),
    cloup.option("-c", "--category", type=str, help="Select a category."),
)
@cloup.option_group(
    "Content Information",
    cloup.option(
        "-e",
        "--edit-code",
        type=str,
        help="Use uniq edit code for mediainfo on rentry.co",
    ),
    cloup.option("-i", "--info", type=str, help="Set information."),
    cloup.option("-n", "--note", type=str, help="Put a note in to the description."),
    cloup.option("-m", "--myanimelist", type=str, help="MyAnimeList link."),
    cloup.option("-sm", "--skip-myanimelist", type=str, help="Skip myanimelist."),
)
@cloup.option_group(
    "Media Settings",
    cloup.option(
        "-p",
        "--pictures-number",
        type=int,
        default=3,
        help="Number of pictures to upload (default: 3).",
    ),
    cloup.option(
        "-pe",
        "--picture-extension",
        type=str,
        default="png",
        help="Extension of the snapshot to upload.",
    ),
    cloup.option(
        "-M",
        "--no-mediainfo",
        is_flag=True,
        help="Do not attach mediainfo to the torrent.",
    ),
    cloup.option(
        "-o",
        "--overwrite",
        is_flag=True,
        help="Recreate the .torrent if it already exists.",
    ),
)
@cloup.option("-ch", "--category-help", is_flag=True, help="Print available categories.")
@cloup.argument("path", type=Path, nargs=-1, required=False)
@cloup.pass_context
def up(ctx, **kwargs):
    """Upload torrents to Nyaa"""
    uploader = NyaaUploader(ctx, SimpleNamespace(**kwargs))

    for file_path in uploader.args.path:
        display_info = Tree("[bold white]Information[not bold]")

        uploader.description = ""
        uploader.file = ""
        uploader.mediainfo = []

        name_plus = []
        dual_audio = False
        multi_audio = False
        multi_sub = False

        name = uploader.get_file_name(file_path)

        style = "red"
        title = "Upload failed"
        if result := uploader.process_file(file_path, display_info):
            display_info = result.display_info
            if uploader.args.auto:
                dual_audio, multi_audio, multi_sub = uploader.detect_audio_subs(
                    result.audio_info, result.sub_info
                )

            uploader.description += "\n\n---\n\n"

            if uploader.is_anime_category and not uploader.args.skip_myanimelist:
                name_plus_ = uploader.process_mal_info(
                    name, uploader.upload_config.info_form_config
                )
                name_plus.extend(name_plus_)
                display_info.add(
                    f"[bold white]MAL link: [cornflower_blue not bold]{uploader.upload_config.info}[white]"
                )

            if dual_audio:
                name_plus.append("Dual-Audio")
            elif multi_audio:
                name_plus.append("Multi-Audio")
            if multi_sub:
                name_plus.append("Multi-Subs")

            display_name = uploader.format_display_name(name, name_plus)

            for provider in uploader.providers:
                ok_cookies = uploader.check_cookies(provider)
                if uploader.upload_config.pic_num > 0 and not ok_cookies:
                    if images := snapshot(uploader, uploader.file, name, uploader.mediainfo):
                        display_info.add(images)

                iprint("Uploading to Nyaa...")
                upload_result = uploader.try_upload_with_retries(display_name, name, provider)

                if upload_result:
                    if (
                        uploader.upload_config.telegram_enabled
                        and not uploader.upload_config.hidden
                    ):
                        uploader.send_notification(upload_result)

                    display_info = uploader.display_success(display_info, upload_result, provider)

                    if ok_cookies and uploader.upload_config.pic_num > 0:
                        display_info = uploader.handle_image_upload(
                            upload_result,
                            display_info,
                            file_path,
                            provider,
                        )

                    style = "bold green"
                    title = "Torrent successfully uploaded!"
                else:
                    style = "yellow"
                    title = "Upload completed with warnings"

        print("")
        rich_print(Panel.fit(display_info, title=title, border_style=style))
