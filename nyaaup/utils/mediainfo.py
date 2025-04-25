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
    "DTS-UHD": "DTS",
}
CHANNEL_MAP = {
    "1": "1.0",
    "2": "2.0",
    "6": "5.1",
    "8": "7.1",
}


def parse_mediainfo(self, file_path: Path) -> str | None:
    try:
        self.mediainfo = _get_mediainfo(file_path)

        if not self.mediainfo[0]["Duration"] or any(
            m.get("@type", "") in ("Audio", "General") and not m.get("BitRate")
            for m in self.mediainfo
        ):
            self.mediainfo = _get_mediainfo(file_path, 1)
    except Exception as e:
        eprint(f"MediaInfo error: {e}")
        return None


def _get_mediainfo(file_path: Path, parse_speed: float = 0.5) -> dict:
    mediainfo = {}
    try:
        mediainfo = json.loads(
            MediaInfo.parse(file_path, output="JSON", parse_speed=parse_speed, full=True)
        )
    except Exception as e:
        wprint(f"Failed to get mediainfo: {e}")

    return mediainfo.get("media", {}).get("track", {})


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
        if track_name in {"CC", "SDH", "Forced", "Dubtitle", "MTL"}:
            return f"**{lang}** [{track_name}]"
        if r := re.search(r"(.*) \((CC|SDH|Forced|Dubtitle|MTL)\)", track_name):
            return f"**{lang}** ({r[1]}) [{r[2]}]"
        else:
            return f"**{lang}** ({track_name})"
    else:
        return f"**{lang}**"


def get_description(mediainfo: list) -> tuple[str, list[str], int, list[str], int]:
    video_info = ""
    audio_info: list[str] = []
    audio_len = set()
    subtitle_info: list[str] = []
    subtitle_len = set()

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

            level = f"**{info.get('Format_Profile')}@L{info.get('Format_Level')}**"

            if "None" in level:
                level = ""
            else:
                codec = codec + " "

            video_info += ", ".join(
                [
                    x
                    for x in [
                        f"**{codec}{level}**",
                        f"**{info.get('Width')}x{info.get('Height')}**" + v_bitrate,
                        f"**{info.get('FrameRate_String')}**",
                    ]
                    if x
                ]
            )

            video_t_num += 1

        elif info["@type"] == "Audio":
            audio_len.add(info.get("Language", ""))
            a_bitrate = ""
            try:
                a_bitrate = f" @ {round(float(info['BitRate']) / 1000)} kbps"
            except KeyError:
                wprint("Couldn't get audio bitrate!")
            atmos = "JOC" in info.get("Format_AdditionalFeatures", "")

            audio_info.append(
                ", ".join(
                    [
                        x
                        for x in [
                            get_track_info(info),
                            f"{AUDIO_CODEC_MAP.get(info['Format'], info['Format'])}"
                            + f"{CHANNEL_MAP.get(info.get('Channels', ''), '?')}"
                            + f"{' Atmos' if atmos else ''}"
                            + a_bitrate,
                        ]
                        if x
                    ]
                )
            )

        elif info["@type"] == "Text":
            subtitle_len.add(info.get("Language", ""))
            subtitle_info.append(
                ", ".join(
                    [
                        x
                        for x in [
                            get_track_info(info),
                            f"{SUB_CODEC_MAP.get(info['Format'], info['Format'])}",
                        ]
                        if x
                    ]
                )
            )

    if video_t_num != 1:
        eprint(f"Multiple videos detected ({video_t_num})!", True)

    if not audio_info:
        eprint("No audio tracks found!", True)

    if not subtitle_info:
        wprint("No subtitle tracks found\n")

    return video_info, audio_info, len(audio_len), subtitle_info, len(subtitle_len)
