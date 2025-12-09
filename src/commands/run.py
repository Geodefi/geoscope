from typing import Any

import click

from src.commands.utils.config import setup_config
from src.commands.utils.env import set_env_var
from src.commands.utils.generator import generate_options
from src.globals import get_logger
from src.globals.schemas.config import CONFIG_SCHEMA
from src.setup import run_daemons, setup


@generate_options(CONFIG_SCHEMA)
@click.option(  # TODO:(5) implement this: search for raise, put a log statmnt on all, check for traceback then log accordingly.
    "--traceback",
    is_flag=True,
    required=False,
    default=False,
    help="Will print the full Exception traceback. Useful for developers.",
)
@click.option(
    "--main-dir",
    envvar="GEOSCOPE_MAIN_DIR",
    type=click.STRING,
    required=False,
    is_eager=True,
    callback=setup_config,
    default=".geoscope",
    help="Relative path for the directory that will be used to store data. Default is .geoscope",
)
@click.option(
    "--chain",
    envvar="GEOSCOPE_CHAIN",
    type=click.Choice(["holesky", "ethereum"]),
    required=True,
    is_eager=True,
    default="holesky",
    callback=set_env_var,
    prompt="You forgot to specify the chain:",
    help="Network name, such as 'holesky' or 'ethereum' etc.",
)
@click.option(
    "--private-key",
    envvar="GEOSCOPE_PRIVATE_KEY",
    required=False,
    type=click.STRING,
    is_eager=True,
    callback=set_env_var,
    help="Private key for the Node Operator maintainer that will run geoscope."
    " Overrides .env file.",
)
@click.option(
    "--api-key-execution",
    envvar="API_KEY_EXECUTION",
    required=False,
    type=click.STRING,
    is_eager=True,
    callback=set_env_var,
    help=(
        "Api key for the execution layer endpoint."
        " Could be the rest api of the execution client. Overrides .env file."
    ),
)
@click.option(
    "--api-key-consensus",
    envvar="API_KEY_CONSENSUS",
    required=False,
    type=click.STRING,
    is_eager=True,
    callback=set_env_var,
    help=(
        "Api key for the consensus layer endpoint."
        " Could be the rest api of the consensus client."
        " Overrides .env file."
    ),
)
@click.option(
    "--api-key-gas",
    envvar="API_KEY_GAS",
    required=False,
    type=click.STRING,
    is_eager=True,
    callback=set_env_var,
    help="Api key for the endpoint used fetching gas prices in gwei. Overrides .env file.",
)
@click.option(
    "--email-password",
    envvar="GEOSCOPE_EMAIL_PASSWORD",
    required=False,
    type=click.STRING,
    is_eager=True,
    callback=set_env_var,
    help="Private key for the Node Operator maintainer who will run geoscope."
    " Overrides .env file.",
)
@click.command(help="Start geoscope.")
def main(main_dir: str, traceback: bool, **kwargs: Any) -> None:
    """
    Main function of the program.
    This function is called with `geoscope run`.
    Initializes the app, logger and database tables, then starts the daemons.

    In the options above, the eager ones are interpreted first.
    Among the multiple eager options, ones that are closer to the bottom have a priority.

    With that being said, a flags or envvar will override both config.json and .env files.
    Flags will also override envvars.
    So, order of priority is: Flags -> Environment Variables -> config.json and .env
    """
    try:
        setup(main_dir=main_dir, setup_logger=True, setup_sdk=True, setup_db=True, verify=True)
        run_daemons()  # TODO:(5) maybe traceback belongs here?

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(str(e))
        get_logger().error("Could not initiate geoscope")
        get_logger().info("Exiting...")

        if traceback:
            raise e
