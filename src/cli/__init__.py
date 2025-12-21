"""
Modern Click-based CLI for Cursor Chat Extractor.

This module provides the main Click group and entry point for the refactored CLI.
Commands are organized in the commands/ subpackage.
"""
import click
import logging
import sys

from .context import CLIContext

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)


@click.group()
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """
    Cursor Chat Extractor - Tools for working with Cursor AI chat logs.

    This CLI provides commands for extracting, converting, searching, and managing
    chat data from the Cursor AI editor.
    """
    # Create context and store in Click's context object
    ctx.obj = CLIContext(verbose=verbose)

    # Configure logging level based on verbosity
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.result_callback()
@click.pass_context
def cleanup(ctx, result, **kwargs):
    """
    Clean up resources after command execution.

    This callback is called after every command completes (or fails).
    Ensures database connections are properly closed, which is critical
    for WAL mode to checkpoint the write-ahead log.
    """
    if ctx.obj:
        ctx.obj.close()


# Import and register command groups here as they're migrated
# Phase 2: Simple commands (info, list, view)
from .commands.misc import info, list, view

cli.add_command(info)
cli.add_command(list)
cli.add_command(view)

# Phase 3: Extract/convert commands
from .commands.extract import extract, convert

cli.add_command(extract)
cli.add_command(convert)

# Tag commands
from .commands.tag import tag
cli.add_command(tag)


def main():
    """
    Main entry point for the CLI.

    Used by __main__.py when USE_NEW_CLI environment variable is set.
    """
    try:
        cli()
    except Exception as e:
        click.secho(f"Error: {e}", fg='red', err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
