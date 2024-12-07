import functools

from rich.console import Console

from nyaaup import __version__


def command_header(f):
    """Decorator to add header banner to commands"""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        Console().print(
            f"[b]nyaaup[/b] [magenta bold]v{__version__}[/]\n\n[dim]Auto torrent uploader to Nyaa\n",
            justify="center",
        )

        return f(*args, **kwargs)

    return wrapper
