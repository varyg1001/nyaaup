# Nyaaup

Nyaaup is an auto uploader to [Nyaa sites](https://github.com/nyaadevs/nyaa), mainly for videos.

## Requirements

- [Python](https://python.org/) 3.10 to 3.13
- [UV](https://docs.astral.sh/uv/) (to install Python package dependencies)

### Dependencies

- [FFmpeg](https://ffmpeg.org/) for image generating.
- [ImageMagick](https://imagemagick.org/script/download.php) for pyoxipng

### Installation

#### pypi

```shell
pip install nyaaup
```

#### from source

1. `git clone https://github.com/varyg1001/nyaaup`
1. `cd nyaaup`
1. `python install.py` or `uv sync --frozen`
1. `nyaaup -h`

### Usage

#### up

```
Usage: nyaaup up [OPTIONS] [PATH]...

   Upload torrents to Nyaa

Upload Tags:
   -u, --uncensored              Use Uncensored tag in title.
   -ms, --multi-subs             Use Multi-Subs tag in title.
   -da, --dual-audio             Use Dual-Audio tag in title.
   -ma, --multi-audios           Use Multi-Audios tag in title.
   -a, --auto / -na, --no-auto   Auto detect Multi-Subs, Multi-Audios or Dual-Audio. (default: True)

Upload Settings:
   -an, --anonymous      Set upload as anonymous.
   -hi, --hidden         Set upload as hidden.
   -co, --complete       Set upload as complete batch.
   -re, --remake         Set upload as remake.
   -s, --skip-upload     Skip torrent upload.
   -c, --category TEXT   Select a category.
   -w, --watch-dir DIR   Path of the watch directory.

Content Information:
   -e, --edit-code TEXT                   Set edit code for Mediainfo on Rentry.co
   -i, --info TEXT                        Set information.
   -n, --note TEXT                        Put a note in to the description.
   -ad, --advert TEXT                     Put advert in to the description.
   -t, --telegram                         Post to telegram.
   -l, --link URL                         Link to set anime manually.
   -sl, --skip-database                   Skip anime database.
   -d, --database [myanimelist|anilist]   Anime database to use for info. (Default: myanimelist)

Media Settings:
   -p, --pictures-number EXTENSION         Number of pictures to use (default: 3).
   -pe, --picture-extension NUM            Extension of the pictures.
   -M, --no-mediainfo                      Do not attach Mediainfo to the torrent.
   -o, --overwrite / -no, --no-overwrite   Create torrent file even if exists. (default: True)

Other options:
   -ch, --category-help   Print available categories.
   -h, --help             Show this message and exit.
```

#### auth

```
Usage: nyaaup auth [OPTIONS]

   Authenticate and configure settings

Config File:
   -c, --credential USER:PASS   Add or replace credential.
   -a, --announces NAME         Add new announces url to config.
   --proxy NAME                 Add or replace proxy to use for uploading to nyaa site.
   -d, --domain NAME            Add or replace domain name for nyaa site.
   -p, --provider NAME          Provider name for config.

Other options:
   -co, --cookie path   Cookies file from nyaa. (Cookies must be in the standard Netscape cookies file format)
   -h, --help           Show this message and exit.
```

### Example commands

```shell
nyaaup auth -c user:pass
```

```shell
nyaaup -p 5 -c 1 -a -m https://myanimelist.net/anime/58935 /path/example.mkv
```

```shell
nyaaup up -sm -c 1 /path/example_folder
```
