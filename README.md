<p align="center">
<sup><em>Auto torrent uploader to Nyaa.si</em></sup>
</p>

# Nyaaup

Nyaaup is an auto torrent uploader to [Nyaa.si](https://nyaa.si/), for video.
Works both on Linux and windows.

## Requirements

- [Python](https://python.org/) 3.10 or newer
- [Poetry](https://python-poetry.org/) 1.2.0 or newer (to install Python package dependencies)

### Dependencies

- [FFmpeg](https://ffmpeg.org/) for image generating.
- [ImageMagick](https://imagemagick.org/script/download.php) for pyoxipng

### Installation

1. `git clone https://github.com/varyg1001/nyaaup`
2. `cd nyaaup`
3. `poetry config virtualenvs.in-project true` (optional, but recommended)
4. `poetry install`
5. `nyaaup -h`

or for Linux auto installer

```shell
$ ./install.sh
```

### Examples

`$ nyaaup auth -add user:pass`
</br>
`$ nyaaup up -p 5 -c 1 -a -m https://myanimelist.net/anime/50652/ /path/Boku.to.Roboco.S01E06.1080p.AMZN.WEB-DL.DDP2.0.H.264-VARYG.mkv`
</br>
`$ nyaaup up -ms -c 1 /path/My.Master.Has.No.Tail.S01.1080p.AMZN.WEB-DL.DDP2.0.H.264-VARYG`

### Usage

```
                                                   nyaaup v2.2.1

                                          Auto torrent uploader to Nyaa.si

USAGE: nyaaup up [-h] [-ch] [-ms] [-da] [-ma] [-a] [-A] [-H] [-C] [-s] [-e EDIT_CODE] [-p PICTURES_NUMBER]
                 [-n NOTE] [-M] [-m MYANIMELIST] [--skip-myanimelist] [-c CATEGORY] [-o]


╭─ Positional arguments ────────────────────────────────────────────────────────────────────────────────────────────╮
│   path                                   File or directory to upload.                                             │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│   -h, --help                             show this help message and exit                                          │
│   -ch, --category-help                   Print available categories.                                              │
│   -ms, --multi-subs                      Add Multi Subs tag to title.                                             │
│   -da, --dual-audios                     Add Dual audios tag to title.                                            │
│   -ma, --multi-audios                    Add Multi audios tag to title.                                           │
│   -a, --auto                             Detect multi subs, multi audios and dual audios.                         │
│   -A, --anonymous                        Upload torrent as anonymous.                                             │
│   -H, --hidden                           Upload the torrent as hidden.                                            │
│   -C, --complete                         If the torrnet is a complete batch.                                      │
│   -s, --skip-upload                      Skip torrent upload.                                                     │
│   -e, --edit-code EDIT_CODE              Use uniq edit code for mediainfo on rentry.co                            │
│   -p, --pictures-number PICTURES_NUMBER  Number of picture to upload to the torrent (default: 3).                 │
│   -n, --note NOTE                        Put a note in to the description.                                        │
│   -M, --no-mediainfo                     Do not attach mediainfo to the torrent (provider rentry.co).             │
│   -m, --myanimelist MYANIMELIST          MyAnimeList link.                                                        │
│   --skip-myanimelist                     Skip anything that connect to MyAnimeList (in case of downtime).         │
│   -c, --category CATEGORY                Select a category, for help use: --category-help (1-6).                  │
│   -o, --overwrite                        Recreate the .torrent if it already exists.                              │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

![img](https://i.kek.sh/6ggTz484hs7.png)
<!---https://i.kek.sh/6ggTz484hs7.png--->
