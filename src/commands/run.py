# -*- coding: utf-8 -*-
import click
from src.utils.env import (
    load_env,
)


@click.option(
    "--chain",
    envvar="GEONIUS_CHAIN",
    required=True,
    type=click.Choice(["holesky", "ethereum"]),
    prompt="You forgot to specify the chain:",
    default="holesky",
    help="Network name, such as 'holesky' or 'ethereum' etc.",
)
@click.option(
    "--main-dir",
    envvar="GEONIUS_DIR",
    required=False,
    type=click.STRING,
    is_eager=False,
    callback=load_env,
    default=".geonius",
    help="Relative path for the directory that will be used to store data."
    " Default is ./.geonius",
)
@click.command(help="Start geoscope.")
def main(**kwargs):
    """Main function of the program.
    This function is called with `geoscope run`.
    Initializes the databases and starts the daemons."""
    pass
