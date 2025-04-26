import re
import shutil
from pathlib import Path
from types import SimpleNamespace

from platformdirs import PlatformDirs
from rich import print
from ruamel.yaml import YAML

from nyaaup.utils.logging import eprint


class Config:
    def __init__(self):
        self.cookies: dict[str, str] = {}
        self.yaml = YAML()
        self.config_data = {}
        self.credentials = SimpleNamespace(username=None, password=None)

        self._dirs = PlatformDirs(appname="nyaaup", appauthor=False)
        self._dirs.user_config_path.mkdir(parents=True, exist_ok=True)
        self.config_path = Path(self._dirs.user_config_path / "nyaaup.yaml")
        self.cookies_path = Path(self._dirs.user_config_path / "cookies.txt")

        self._load()

        if self.cookies_path.exists():
            self._get_cookies()

    @property
    def dirs(self):
        return self._dirs

    def _get_cookies(self):
        """Load cookies from file if it exists"""
        data = self.cookies_path.read_text().splitlines()
        for x in data:
            if (
                x
                and not x.startswith("#")
                and (values := x.split("\t"))
                and values[-2] != "__ddg9__"
            ):
                self.cookies[values[-2]] = values[-1]

    def _create(self) -> None:
        """Create default config file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(
            Path(__file__).resolve().parent.parent.with_name("nyaaup.yaml.example"),
            self.config_path,
        )
        eprint(f"Config file doesn't exist, created at: {self.config_path}", fatal=True)

    def _load(self) -> None:
        """Load config from file"""
        try:
            self.config_data = self.yaml.load(self.config_path)
        except FileNotFoundError:
            self._create()

    def load_credentials(self, cred: str) -> None:
        """Parse credentials string into username/password"""
        if cred == "user:pass":
            eprint("Set valid credentials!", True)
        if return_cred := re.fullmatch(r"^([^:]+?):([^:]+?)(?::(.+))?$", cred):
            cred_ = return_cred.groups()
            self.credentials = SimpleNamespace(username=cred_[0], password=cred_[1])
        else:
            eprint("Incorrect credentials format! (Format: `user:pass`)", True)

    def update(self, data: dict) -> None:
        """Update config file with new data"""
        try:
            self.yaml.dump(data, self.config_path)
        except FileNotFoundError:
            self._create()
            self.update(data)

        print("\n[bold green]Config successfully updated![white]")

    def get(self, key, default=None) -> str | dict:
        """Get value from config_data with optional default"""
        return self.config_data.get(key, default)

    def __getitem__(self, key):
        """Allow bracket notation access to config_data"""
        return self.config_data.get(key)

    def __contains__(self, key):
        """Support 'in' operator for checking if key exists"""
        return key in self.config_data
