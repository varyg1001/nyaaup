import sys
import shutil
from pathlib import Path
from types import SimpleNamespace

import cloup

from nyaaup.utils.auth import DEFAULT_PROVIDER, AuthConfig, AuthHandler
from nyaaup.utils.userconfig import Config
from nyaaup.utils.logging import iprint, wprint


@cloup.command()
@cloup.option_group(
    "Config File",
    cloup.option(
        "-c",
        "--credential",
        type=str,
        metavar="USER:PASS",
        help="Add or replace credential.",
    ),
    cloup.option(
        "-a",
        "--announces",
        type=str,
        metavar="NAME",
        help="Add new announces url to config.",
    ),
    cloup.option(
        "--proxy",
        type=str,
        metavar="NAME",
        help="Add or replace proxy to use for uploading to nyaa site.",
    ),
    cloup.option(
        "-d",
        "--domain",
        type=str,
        metavar="NAME",
        help="Add or replace domain name for nyaa site.",
    ),
    cloup.option(
        "-p",
        "--provider",
        type=str,
        metavar="NAME",
        default=DEFAULT_PROVIDER,
        help="Provider name for config.",
    ),
)
@cloup.option(
    "-co",
    "--cookie",
    type=Path,
    default=None,
    metavar="path",
    help="Cookies file from nyaa. (Cookies must be in the standard Netscape cookies file format)",
)
@cloup.pass_context
def auth(ctx, **kwargs):
    """Authenticate and configure settings"""
    if any(x in sys.argv for x in ctx.help_option_names):
        return

    if len(sys.argv) == 1:
        print(ctx.get_help())
        sys.exit(1)

    args = SimpleNamespace(**kwargs)
    config = Config()

    if args.cookie:
        if config.cookies_path.exists():
            wprint("Cookie file already exists.")
        shutil.copy(args.cookie, config.cookies_path)
        iprint("Cookie file copied to config directory.", 0, 0)
    
    if args.credential:
        auth_config = AuthConfig.from_args(args)

        handler = AuthHandler(config.config_data, auth_config)
        handler.validate_inputs()
        handler.process_credential(config)
        handler.find_provider()
        handler.update_provider()

        config.update(handler.config)
