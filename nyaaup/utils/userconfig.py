import re
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, NoReturn
from platformdirs import PlatformDirs

from ruamel.yaml import YAML

from nyaaup.utils.logging import eprint


class Config:
    def __init__(self):
        self.dirs = PlatformDirs(appname="nyaaup", appauthor=False)
        self.config_path = Path(self.dirs.user_config_path / "nyaaup.yaml")
        self.cookies_path = Path(self.dirs.user_config_path / "cookies.txt")
        self.cookies = {}
        self.yaml = YAML()
        self.get_cookies()

    @property
    def get_dirs(self):
        return self.dirs

    def get_cookies(self):
        """Load cookies from file if it exists"""
        if self.cookies_path.exists():
            data = self.cookies_path.read_text().splitlines()
            for x in data:
                if (
                    x
                    and not x.startswith("#")
                    and (values := x.split("\t"))
                    and values[-2] != "__ddg9__"
                ):
                    self.cookies[values[-2]] = values[-1]

    def create(self, exit=False) -> Dict:
        """Create default config file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(
            Path(__file__).resolve().parent.with_name("nyaaup.yaml.example"),
            self.config_path,
        )
        eprint(f"Config file doesn't exist, created at: {self.config_path}", fatal=exit)
        return self.load(exit)

    def load(self, exit=True) -> Dict:
        """Load config from file"""
        try:
            return self.yaml.load(self.config_path)
        except FileNotFoundError:
            return self.create(exit)

    @staticmethod
    def get_cred(cred: str) -> SimpleNamespace | NoReturn:
        """Parse credentials string into username/password"""
        if cred == "user:pass":
            eprint("Set valid credentials!", True)
        if return_cred := re.fullmatch(r"^([^:]+?):([^:]+?)(?::(.+))?$", cred):
            cred_ = return_cred.groups()
            return SimpleNamespace(**{"username": cred_[0], "password": cred_[1]})
        else:
            eprint("Incorrect credentials format! (Format: `user:pass`)", True)

    def update(self, data: Dict):
        """Update config file with new data"""
        try:
            self.yaml.dump(data, self.config_path)
        except FileNotFoundError:
            self.create()
            self.update(data)
        from rich import print

        print("[bold green]\nConfig successfully updated![white]")
