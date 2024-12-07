import json
import re
from pathlib import Path

from langcodes import Language
from pymediainfo import MediaInfo

from nyaaup.utils.logging import eprint, wprint

SUB_CODEC_MAP = {"UTF-8": "SRT"}
AUDIO_CODEC_MAP = {
    "E-AC-3": "DDP",
    "AC-3": "DD",
    "fLaC": "FLAC",
}
CHANNEL_MAP = {
    "1": "1.0",
    "2": "2.0",
    "6": "5.1",
    "8": "7.1",
}


def parse_mediainfo(file_path: Path, parse_speed: float = 0.5) -> dict:
    try:
        mediainfo = MediaInfo.parse(file_path, output="JSON", full=True)
        info = json.loads(mediainfo)
        if not info or "media" not in info:
            raise ValueError("Invalid MediaInfo output")

        tracks = info["media"]["track"]

        # Check if we need detailed parsing
        needs_reparse = not tracks[0].get("Duration")
        if not needs_reparse:
            for track in tracks:
                if track.get("@type") == "Audio" and not track.get("BitRate"):
                    needs_reparse = True
                    break

        if needs_reparse:
            mediainfo = MediaInfo.parse(file_path, output="JSON", parse_speed=1, full=True)
            tracks = json.loads(mediainfo)["media"]["track"]

        return tracks
    except Exception as e:
        eprint(f"MediaInfo error: {e}")
        return None


def get_track_info(data: dict) -> str:
    lang = data.get("Language")
    if not lang:
        lang = "Und"
        wprint("One track has unknown language!")
    else:
        lang = Language.get(lang).display_name()
    track_name = data.get("Title")

    if track_name and "(" in lang:
        lang = lang.split(" (")[0]
        return get_return(lang, track_name)
    elif "(" in lang:
        lang = lang.split(" (")[0]
        return get_return(lang)
    elif track_name:
        return get_return(lang, track_name)
    else:
        return get_return(lang)


def get_return(lang: str, track_name: str | None = None) -> str:
    if track_name:
        if track_name in {"CC", "SDH", "Forced", "Dubtitle"}:
            return f"**{lang}** [{track_name}]"
        if r := re.search(r"(.*) \((CC|SDH|Forced|Dubtitle)\)", track_name):
            return f"**{lang}** ({r[1]}) [{r[2]}]"
        else:
            return f"**{lang}** ({track_name})"
    else:
        return f"**{lang}**"


def get_description(mediainfo: list) -> tuple[str, list[str], list[str]]:
    video_info = ""
    audio_info: list[str] = []
    subtitles_info: list[str] = []

    video_t_num = 0

    for info in mediainfo:
        if info["@type"] == "Video":
            v_bitrate = ""
            try:
                b_raw = float(float(info["StreamSize"]) * 8 / float(info["Duration"]))
                if b_raw / 1000 < 10000:
                    b = f"{b_raw / 1000:.0f} kbps"
                else:
                    b = f"{b_raw / 1000000:.2f} Mbps"
                v_bitrate = f" @ **{b}**"
            except KeyError:
                wprint("Couldn't get video bitrate!")

            codec = ""
            if codec_ := info.get("InternetMediaType"):
                codec = codec_.split("/")[1] + " "
            elif codec_ := info.get("Format"):
                codec = codec_
            level = f'**{info.get("Format_Profile")}@L{info.get("Format_Level")}**'
            if "None" in level:
                level = ""
            else:
                codec = codec + " "

            video_info += ", ".join(
                [
                    x
                    for x in [
                        f"**{codec}{level}**",
                        f'**{info.get("Width")}x{info.get("Height")}**' + v_bitrate,
                        f'**{info.get("FrameRate_String")}**',
                    ]
                    if x
                ]
            )

            video_t_num += 1

        elif info["@type"] == "Audio":
            a_bitrate = ""
            try:
                a_bitrate = f" @ {round(float(info['BitRate'])/1000)} kbps"
            except KeyError:
                wprint("Couldn't get audio bitrate!")
            atmos = "JOC" in info.get("Format_AdditionalFeatures", "")

            audio_info.append(
                ", ".join(
                    [
                        x
                        for x in [
                            get_track_info(info),
                            f'{AUDIO_CODEC_MAP.get(info["Format"], info["Format"])}'
                            + f'{CHANNEL_MAP.get(info.get("Channels", ""), "?")}'
                            + f'{" Atmos" if atmos else ""}'
                            + a_bitrate,
                        ]
                        if x
                    ]
                )
            )

        elif info["@type"] == "Text":
            subtitles_info.append(
                ", ".join(
                    [
                        x
                        for x in [
                            get_track_info(info),
                            f'{SUB_CODEC_MAP.get(info["Format"], info["Format"])}',
                        ]
                        if x
                    ]
                )
            )

    if video_t_num != 1:
        eprint(f"Multiple videos detected ({video_t_num})!", True)

    if not audio_info:
        eprint("No audio tracks found!", True)

    if not subtitles_info:
        wprint("No subtitle tracks found")

    return video_info, audio_info, subtitles_info
