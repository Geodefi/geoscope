# -*- coding: utf-8 -*-
import click
from src.utils.env import (
    load_env,
    set_geoscope_private_key,
    set_api_key_execution,
    set_api_key_consensus,
    set_api_key_gas,
    set_email_password,
)
from src.globals import get_logger
from src.setup import setup, init_dbs, run_daemons


def config_reset(ctx, _option, value):
    if not value or ctx.resilient_parsing:
        return value

    click.confirm("Are you sure you want to drop the db?", abort=True)
    return value


@click.option(
    "--chain-start",
    required=False,
    type=click.INT,
    help="The first block to be considered for events within given chain.",
)
@click.option(
    "--chain-identifier",
    required=False,
    type=click.Choice(["latest", "earliest", "pending", "safe", "finalized"]),
    help="Identifier fetching new blocks.",
)
@click.option(
    "--chain-period",
    required=False,
    type=click.INT,
    help="The amount of 'chain-interval' before checking for new blocks.",
)
@click.option(
    "--chain-interval",
    required=False,
    type=click.INT,
    help="Average block time to rely on for given chain.",
)
@click.option(
    "--chain-range",
    required=False,
    type=click.INT,
    help="Maximum block to use when grouping a range of blocks.",
)
@click.option(
    "--chain-execution-api",
    required=False,
    type=click.STRING,
    help="Api endpoint for the execution layer. Could be the rest api of the execution client.",
)
@click.option(
    "--chain-consensus-api",
    required=False,
    type=click.STRING,
    help="Api endpoint for the consensus layer. Could be the rest api of the consensus client.",
)
@click.option(
    "--network-refresh-rate",
    required=False,
    type=click.IntRange(0, 360),
    help="Cached data will be refreshed after provided delay (s).",
)
@click.option(
    "--network-attempt-rate",
    required=False,
    type=click.IntRange(0, 10),
    help="Interval between api requests (s).",
)
@click.option(
    "--network-max-attempt",
    required=False,
    type=click.IntRange(0, 100),
    help="Api requests will fail after these many call attempts.",
)
@click.option(
    "--no-log-file",
    is_flag=True,
    help="Don't store log messages in a file.",
)
@click.option(
    "--no-log-stream",
    is_flag=True,
    help="Don't print log messages to the terminal.",
)
@click.option(
    "--logger-dir",
    required=False,
    type=click.STRING,
    help="Directory name that log files will be stored.",
)
@click.option(
    "--logger-level",
    required=False,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Set logging level for both stream and log file.",
)
@click.option(
    "--logger-when",
    required=False,
    type=click.Choice(
        ["S", "M", "H", "D", "W0", "W1", "W2", "W3", "W4", "W5", "W6", "midnight"],
    ),
    help="When should logger continues with a new file.",
)
@click.option(
    "--logger-interval",
    required=False,
    type=click.INT,
    help="How many intervals before logger continue with a new file.",
)
@click.option(
    "--logger-backup",
    required=False,
    type=click.INT,
    help="The number of maximum logger files that will be kept. After that, will delete the oldest ones.",
)
@click.option(
    "--database-dir",
    required=False,
    type=click.STRING,
    help="Directory name for database.",
)
@click.option(
    "--reset",
    required=False,
    is_eager=True,
    is_flag=True,
    callback=config_reset,
    help="Resets the database and start over.Suggested after a new update or unexpected error.",
)
@click.option(
    "--private-key",
    envvar="GEOSCOPE_PRIVATE_KEY",
    required=False,
    type=click.STRING,
    is_eager=True,
    callback=set_geoscope_private_key,
    help="Private key for the Node Operator maintainer that will run geoscope."
    "Overrides .env file.",
)
@click.option(
    "--api-key-execution",
    envvar="API_KEY_EXECUTION",
    required=False,
    type=click.STRING,
    is_eager=True,
    callback=set_api_key_execution,
    help="Api key for the execution layer endpoint."
    " Could be the rest api of the execution client. Overrides .env file.",
)
@click.option(
    "--api-key-consensus",
    envvar="API_KEY_CONSENSUS",
    required=False,
    type=click.STRING,
    is_eager=True,
    callback=set_api_key_consensus,
    help="Api key for the consensus layer endpoint."
    " Could be the rest api of the consensus client."
    " Overrides .env file.",
)
@click.option(
    "--api-key-gas",
    envvar="API_KEY_GAS",
    required=False,
    type=click.STRING,
    is_eager=True,
    callback=set_api_key_gas,
    help="Api key for the endpoint used fetching gas prices in gwei. Overrides .env file.",
)
@click.option(
    "--email-password",
    envvar="EMAIL_PASSWORD",
    required=False,
    type=click.STRING,
    is_eager=True,
    callback=set_email_password,
    help="Private key for the Node Operator maintainer who will run geoscope."
    " Overrides .env file.",
)
@click.option(
    "--chain",
    envvar="GEOSCOPE_CHAIN",
    required=True,
    type=click.Choice(["holesky", "ethereum"]),
    prompt="You forgot to specify the chain:",
    default="holesky",
    help="Network name, such as 'holesky' or 'ethereum' etc.",
)
@click.option(
    "--main-dir",
    envvar="GEOSCOPE_DIR",
    required=False,
    type=click.STRING,
    is_eager=False,
    callback=load_env,
    default=".geoscope",
    help="Relative path for the directory that will be used to store data."
    " Default is ./.geoscope",
)
@click.command(help="Start geoscope.")
def main(**kwargs):
    """Main function of the program.
    This function is called with `geoscope run`.
    Initializes the databases and starts the daemons."""
    try:
        setup(**kwargs, test_email=True, test_ethdo=False, test_operator=True)
        init_dbs(reset=kwargs["reset"])
        run_daemons()

    except Exception as e:
        try:
            get_logger().error(str(e))
            get_logger().error("Could not initiate geoscope")
            get_logger().info("Exiting...")
        except Exception:
            print(str(e) + "\nCould not initiate geoscope.\nExiting...")

        raise e
