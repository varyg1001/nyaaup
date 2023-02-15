<p align="center">
<sup><em>Auto torrent uploader to Nyaa.si</em></sup>
</p>

# Nyaaup

Nyaaup is an auto torrent uploader to [Nyaa.si](https://nyaa.si/), working with `.mkv` videos (primarily for animes and live-actions).
This tool you can use with Linux systems. (On Windows you can use WSL.)

## Requirements

- [Python](https://python.org/) 3.10 or 3.11
- [Poetry](https://python-poetry.org/) 1.2.0 or newer (to install Python package dependencies)

### Dependencies

- [FFmpeg](https://fmpeg.org/) for image generating.
- [MKVToolNix](https://mkvtoolnix.download/downloads.html) to get info from `.mkv` file.

### Installation

```shell
$ ./install.sh
```

### Examples

`$ nyaaup -p 5 -c 1 -A -mal https://myanimelist.net/anime/50652/ /path/Boku.to.Roboco.S01E06.1080p.AMZN.WEB-DL.DDP2.0.H.264-VARYG.mkv`
</br>
`$ nyaaup -ms -c 1 /path/My.Master.Has.No.Tail.S01.1080p.AMZN.WEB-DL.DDP2.0.H.264-VARYG`

### Usage

```
usage: nyaaup [-h] [-ch] [-ms] [-da] [-ma] [-A] [-a] [-H] [-C] [-s] [-e EDIT_CODE] [-p PICTURES_NUMBER]
              [-mal MYANIMELIST]
              [-c {1,Anime - English-translated,2,Anime - Non-English-translated,3,Anime - Raw,4,Live Action - English-translated,5,Live Action - Raw,6,Live Action - Non-English-translate}]
              [-add ADD_CREDENTIAL]
              [path ...]

Nyaa.si auto torrent uploader.

positional arguments:
  path                  File or directory to upload.

options:
  -h, --help            show this help message and exit
  -ch, --category-help  Print available categories.
  -ms, --multi-subs     Add Multi-Subs tag to title.
  -da, --dual-audios    Add Dual-audios tag to title.
  -ma, --multi-audios   Add Multi-audios tag to title.
  -A, --auto            Detect multi-subs, multi-audios and dual-audios (if sub or audio more than one it will add
                        the tags)
  -a, --anonymous       Upload torrent as anonymous.
  -H, --hidden          Upload the torrent as hidden.
  -C, --complete        If the torrnet is a complete batch.
  -s, --skip-upload     Skip torrent upload.
  -e EDIT_CODE, --edit-code EDIT_CODE
                        Use uniq edit code for mediainfo on rentry.co
  -p PICTURES_NUMBER, --pictures-number PICTURES_NUMBER
                        Number of picture to upload to the torrent (default: 3).
  -mal MYANIMELIST, --myanimelist MYANIMELIST
                        MyAnimeList link.
  -c {1,Anime - English-translated,2,Anime - Non-English-translated,3,Anime - Raw,4,Live Action - English-translated,5,Live Action - Raw,6,Live Action - Non-English-translate}, --category {1,Anime - English-translated,2,Anime - Non-English-translated,3,Anime - Raw,4,Live Action - English-translated,5,Live Action - Raw,6,Live Action - Non-English-translate}
                        Select a category to upload the torrent.
  -add ADD_CREDENTIAL, --add-credential ADD_CREDENTIAL
                        Add or replace credential in config file.
```
