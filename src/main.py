"""
Entry point for the application's command-line interface (CLI).

This module sets up the CLI using Click, including version information
and available commands.
"""

import sys

import click

from src.commands.backup import main as backup
from src.commands.reset import main as reset
from src.commands.restore import main as restore
from src.commands.run import main as run
from src.commands.version import main as get_version


@click.group()
@click.version_option(version=get_version())
def cli() -> None:
    """
    Command-line interface (CLI) entry point for the application.

    Defines the main CLI group using the Click library. It includes
    a version option to display the current version of the application.
    """


cli.add_command(backup, "backup")
cli.add_command(reset, "reset")
cli.add_command(restore, "restore")
cli.add_command(run, "run")

if __name__ == "__main__":
    try:
        cli()
    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
        sys.exit(1)
