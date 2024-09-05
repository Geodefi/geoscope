# -*- coding: utf-8 -*-

import click
from src.utils.version import get_version
from src.commands.run import main as run
from src.commands.config import main as config


@click.group()
@click.version_option(version=get_version())
def cli() -> None:
    pass


cli.add_command(run, "run")
cli.add_command(config, "config")

if __name__ == "__main__":
    cli()
