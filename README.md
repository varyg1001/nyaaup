<p align="center">
  <img src="https://forthebadge.com/images/badges/made-with-python.png"/>
</p>
<p align="center">
<sup><em>Auto torrent uploader to Nyaa.si</em></sup>
</p>

# Nyaaup

Nyaaup is an auto torrent uploader to [Nyaa sites](https://github.com/nyaadevs/nyaa), mainly for videos.
Works both on Linux and windows.

## Requirements

- [Python](https://python.org/) 3.10, 3.11 or 3.12
- [Poetry](https://python-poetry.org/) 1.2.0 or newer (to install Python package dependencies)

### Dependencies

- [FFmpeg](https://ffmpeg.org/) for image generating.
- [ImageMagick](https://imagemagick.org/script/download.php) for pyoxipng

### Installation

Run `./install.py` or `./install.sh` to install the tool and its dependencies

#### or

1. `git clone https://github.com/varyg1001/nyaaup`
2. `cd nyaaup`
3. `poetry config virtualenvs.in-project true` (optional, but recommended)
4. `poetry install`
5. `nyaaup -h`

### Examples

```shell
nyaaup auth -c user:pass
```
```shell
nyaaup up -p 5 -c 1 -a -m https://myanimelist.net/anime/50652/ /path/Boku.to.Roboco.S01E06.1080p.AMZN.WEB-DL.DDP2.0.H.264-VARYG.mkv
```
```shell
nyaaup up -ms -c 1 /path/My.Master.Has.No.Tail.S01.1080p.AMZN.WEB-DL.DDP2.0.H.264-VARYG
```

### Usage

```
                                                            nyaaup v4.0.0

                                                    Auto torrent uploader to Nyaa

USAGE: nyaaup up [-h] [-ch] [-ms] [-t] [-da] [-ma] [-a] [-an] [-hi] [-co] [-re] [-s] [-e EDIT_CODE] [-i INFO] [-p PICTURES_NUMBER]
                 [-pe PICTURE_EXTENSION] [-n NOTE] [-M] [-m MYANIMELIST] [--skip-myanimelist] [-c CATEGORY] [-o]


╭─ Positional arguments ─────────────────────────────────────────────────────╮
│   path                                        File or directory to upload. │
╰────────────────────────────────────────────────────────────────────────────╯

╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────╮
│   -h, --help                                  show this help message and exit                                  │
│   -ch, --category-help                        Print available categories.                                      │
│   -ms, --multi-subs                           Add Multi Subs tag to title.                                     │
│   -t, --telegram                              Send telegram message.                                           │
│   -da, --dual-audios                          Add Dual audios tag to title.                                    │
│   -ma, --multi-audios                         Add Multi audios tag to title.                                   │
│   -a, --auto                                  Detect multi subs, multi audios and dual audios.                 │
│   -an, --anonymous                            Upload torrent as anonymous.                                     │
│   -hi, --hidden                               Upload the torrent as hidden.                                    │
│   -co, --complete                             If the torrnet is a complete batch.                              │
│   -re, --remake                               If the torrnet is a remake.                                      │
│   -s, --skip-upload                           Skip torrent upload.                                             │
│   -e, --edit-code EDIT_CODE                   Use uniq edit code for mediainfo on rentry.co                    │
│   -i, --info INFO                             Set information.                                                 │
│   -p, --pictures-number PICTURES_NUMBER       Number of picture to upload to the torrent (default: 3).         │
│   -pe, --picture-extension PICTURE_EXTENSION  Extension of the snapshot to upload (default: png).              │
│   -n, --note NOTE                             Put a note in to the description.                                │
│   -M, --no-mediainfo                          Do not attach mediainfo to the torrent (provider rentry.co).     │
│   -m, --myanimelist MYANIMELIST               MyAnimeList link.                                                │
│   --skip-myanimelist                          Skip anything that connect to MyAnimeList (in case of downtime). │
│   -c, --category CATEGORY                     Select a category, for help use: --category-help.                │
│   -o, --overwrite                             Recreate the .torrent if it already exists.                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

![img](https://i.kek.sh/crb0nguklZk.png)
<!---https://i.kek.sh/crb0nguklZk.png--->
