# -*- coding: utf-8 -*-
import click
from src.utils.env import (
    load_env,
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
    """TODO: (later)"""
    pass
