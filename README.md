<p align="center">
  <img src="https://forthebadge.com/images/badges/made-with-python.png"/>
</p>
<p align="center">
<sup><em>Auto uploader to Nyaa</em></sup>
</p>

# Nyaaup

Nyaaup is an auto uploader to [Nyaa sites](https://github.com/nyaadevs/nyaa), mainly for videos.

## Requirements

- [Python](https://python.org/) 3.10 to 3.13
- [Poetry](https://python-poetry.org/) 2.0.0 or newer (to install Python package dependencies)

### Dependencies

- [FFmpeg](https://ffmpeg.org/) for image generating.
- [ImageMagick](https://imagemagick.org/script/download.php) for pyoxipng

### Installation

#### auto

Run `./install.py` to install the tool and its dependencies

##### manual

1. `git clone https://github.com/varyg1001/nyaaup`
2. `cd nyaaup`
3. `poetry config virtualenvs.in-project true` (optional, but recommended)
4. `poetry install`
5. `nyaaup -h`

### Commands

- up
- auth

### Examples usage

```shell
nyaaup auth -c user:pass
```

```shell
nyaaup -p 5 -c 1 -a -m https://myanimelist.net/anime/50652/ /path/example.mkv
```

```shell
nyaaup -sm -c 1 /path/example_folder
```

### Usage

#### up

```
Usage: nyaaup up [OPTIONS] [PATH]...

   Upload torrents to Nyaa

Upload Tags:
   -ms, --multi-subs     Use Multi-Subs tag in title.
   -da, --dual-audio     Use Dual-Audio tag in title.
   -ma, --multi-audios   Use Multi-Audios tag in title.
   -a, --auto            Detect Multi-Subs, Multi-Audios or Dual-Audio.

Upload Settings:
   -an, --anonymous       Set upload as anonymous.
   -hi, --hidden          Set upload as hidden.
   -co, --complete        Set upload as complete batch.
   -re, --remake          Set upload as remake.
   -s, --skip-upload      Skip torrent upload.
   -c, --category TEXT    Select a category.
   -w, --watch-dir TEXT   Path of the watch directory.

Content Information:
   -e, --edit-code TEXT           Set edit code for Mediainfo on Rentry.co
   -i, --info TEXT                Set information.
   -n, --note TEXT                Put a note in to the description.
   -m, --myanimelist TEXT         MyAnimeList link to use.
   -t, --telegram                 Post to telegram.
   -sm, --skip-myanimelist TEXT   Skip MyAnimeList.

Media Settings:
   -p, --pictures-number INTEGER   Number of pictures to use (default: 3).
   -pe, --picture-extension TEXT   Extension of the pictures.
   -M, --no-mediainfo              Do not attach Mediainfo to the torrent.
   -o, --overwrite                 Create torrent file even if exists.

Other options:
   -ch, --category-help   Print available categories.
   -h, --help             Show this message and exit.
```

#### auth

```
Usage: nyaaup auth [OPTIONS]

   Authenticate and configure settings

Options:
   -c, --credential USER:PASS   Add or replace credential.
   -a, --announces NAME         Add new announces url to config.
   --proxy NAME                 Add or replace proxy to use for uploading to nyaa site.
   -d, --domain NAME            Add or replace domain name for nyaa site.
   -p, --provider NAME          Provider name for config.
   -h, --help                   Show this message and exit.
```
