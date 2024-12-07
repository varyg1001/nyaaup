<p align="center">
  <img src="https://forthebadge.com/images/badges/made-with-python.png"/>
</p>
<p align="center">
<sup><em>Auto torrent uploader to Nyaa</em></sup>
</p>

# Nyaaup

Nyaaup is an auto torrent uploader to [Nyaa sites](https://github.com/nyaadevs/nyaa), mainly for videos.
Works both on Linux and windows.

## Requirements

- [Python](https://python.org/) 3.10 to 3.13
- [Poetry](https://python-poetry.org/) 1.2.0 or newer (to install Python package dependencies)

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

### Examples usage

```shell
nyaaup auth -c user:pass
```

```shell
nyaaup -p 5 -c 1 -a -m https://myanimelist.net/anime/50652/ /path/example.mkv
```

```shell
nyaaup -ms -c 1 /path/example_folder
```

### Usage

#### up

```
Usage: nyaaup up [OPTIONS] [PATH]...

   Upload torrents to Nyaa

Upload Tags:
   -ms, --multi-subs     Add Multi Subs tag to title.
   -da, --dual-audios    Add Dual audios tag to title.
   -ma, --multi-audios   Add Multi audios tag to title.
   -a, --auto            Detect multi subs, multi audios and dual audios.

Upload Settings:
   -an, --anonymous      Upload torrent as anonymous.
   -hi, --hidden         Upload the torrent as hidden.
   -co, --complete       If the torrnet is a complete batch.
   -re, --remake         If the torrnet is a remake.
   -s, --skip-upload     Skip torrent upload.
   -c, --category TEXT   Select a category.

Content Information:
   -e, --edit-code TEXT           Use uniq edit code for mediainfo on rentry.co
   -i, --info TEXT                Set information.
   -n, --note TEXT                Put a note in to the description.
   -m, --myanimelist TEXT         MyAnimeList link.
   -sm, --skip-myanimelist TEXT   Skip myanimelist.

Media Settings:
   -p, --pictures-number INTEGER   Number of pictures to upload (default: 3).
   -pe, --picture-extension TEXT   Extension of the snapshot to upload.
   -M, --no-mediainfo              Do not attach mediainfo to the torrent.
   -o, --overwrite                 Recreate the .torrent if it already exists.

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

![img](https://i.kek.sh/crb0nguklZk.png)
<!---https://i.kek.sh/crb0nguklZk.png--->
