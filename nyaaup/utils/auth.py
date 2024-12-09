from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from nyaaup.utils.logging import eprint, wprint
from nyaaup.utils.userconfig import Config

DEFAULT_ANNOUNCE = "http://nyaa.tracker.wf:7777/announce"
DEFAULT_DOMAIN = "https://nyaa.si"
DEFAULT_PROVIDER = "nyaasi"


@dataclass
class AuthConfig:
    """Configuration data structure for auth command"""

    name: str
    domain: str
    proxy: str | None
    announces: list[str]
    credential: str | None

    @classmethod
    def from_args(cls, args: SimpleNamespace) -> "AuthConfig":
        """Create AuthConfig from command arguments"""
        return cls(
            name=args.provider or DEFAULT_PROVIDER,
            domain=args.domain or DEFAULT_DOMAIN,
            proxy=args.proxy,
            announces=[args.announces] if args.announces else [],
            credential=args.credential,
        )


class AuthHandler:
    """Handles authentication and configuration logic"""

    def __init__(self, config: dict[str, Any], auth_config: AuthConfig):
        self.config = config
        self.auth_config = auth_config
        self.provider = None

    def validate_inputs(self) -> None:
        """Validate command inputs"""
        if not (
            self.auth_config.announces or self.auth_config.domain or self.auth_config.credential
        ):
            eprint("No arguments provided!", fatal="exit")

    def process_credential(self, conf: Config) -> None:
        """Process credential if provided"""
        if self.auth_config.credential:
            conf.load_credentials(self.auth_config.credential)

    def find_provider(self) -> None:
        """Find or create provider configuration"""
        if providers := self.config.get("providers"):
            self.provider = next(
                (x for x in providers if x.get("name") == self.auth_config.name), None
            )
        else:
            if not self.auth_config.credential:
                eprint(
                    "Could not find specified provider and no credential provided!",
                    fatal="exit",
                )
            self.config["providers"] = []

    def update_provider(self) -> None:
        """Update or create provider configuration"""
        if not self.provider:
            wprint("Could not find specified provider in the config!")

            announces = self.auth_config.announces
            if DEFAULT_ANNOUNCE not in announces:
                announces.append(DEFAULT_ANNOUNCE)

            self.config["providers"].append(
                {
                    "name": self.auth_config.name,
                    "domain": self.auth_config.domain,
                    "credentials": self.auth_config.credential,
                    "proxy": self.auth_config.proxy,
                    "announces": announces,
                }
            )
        else:
            if self.auth_config.announces:
                self.provider["announces"] += self.auth_config.announces
            if self.auth_config.domain:
                self.provider["domain"] = self.auth_config.domain
            if self.auth_config.credential:
                self.provider["credentials"] = self.auth_config.credential
            if self.auth_config.proxy:
                self.provider["proxy"] = self.auth_config.proxy
