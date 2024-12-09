import sys
from types import SimpleNamespace

import cloup
from cloup import command, option

from nyaaup.utils.auth import DEFAULT_PROVIDER, AuthConfig, AuthHandler
from nyaaup.utils.userconfig import Config


@command()
@option(
    "-c",
    "--credential",
    type=str,
    metavar="USER:PASS",
    help="Add or replace credential.",
)
@option(
    "-a",
    "--announces",
    type=str,
    metavar="NAME",
    help="Add new announces url to config.",
)
@option(
    "--proxy",
    type=str,
    metavar="NAME",
    help="Add or replace proxy to use for uploading to nyaa site.",
)
@option(
    "-d",
    "--domain",
    type=str,
    metavar="NAME",
    help="Add or replace domain name for nyaa site.",
)
@option(
    "-p",
    "--provider",
    type=str,
    metavar="NAME",
    default=DEFAULT_PROVIDER,
    help="Provider name for config.",
)
@cloup.pass_context
def auth(ctx, **kwargs):
    """Authenticate and configure settings"""
    if any(x in sys.argv for x in ctx.help_option_names):
        return

    if len(sys.argv) == 1:
        print(ctx.get_help())
        sys.exit(1)

    config = Config()
    auth_config = AuthConfig.from_args(SimpleNamespace(**kwargs))

    handler = AuthHandler(config.config_data, auth_config)
    handler.validate_inputs()
    handler.process_credential(config)
    handler.find_provider()
    handler.update_provider()

    config.update(handler.config)
