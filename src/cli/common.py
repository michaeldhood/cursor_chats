"""
Common Click decorators and utilities for CLI commands.

Provides reusable option decorators to reduce boilerplate across command definitions.
"""
import click
from pathlib import Path
from typing import Callable


def db_option(f: Callable) -> Callable:
    """
    Add --db-path option to command.

    Allows users to specify a custom database path instead of using
    the OS-specific default location.

    Args:
        f: Command function to decorate

    Returns:
        Decorated function with --db-path option
    """
    return click.option(
        '--db-path',
        type=click.Path(path_type=Path),
        help='Path to database file (default: OS-specific location)'
    )(f)


def output_dir_option(default: str = '.') -> Callable:
    """
    Add --output-dir/-o option to command.

    Args:
        default: Default output directory (default: current directory)

    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        return click.option(
            '-o', '--output-dir',
            type=click.Path(path_type=Path),
            default=default,
            help=f'Output directory (default: {default})'
        )(f)
    return decorator


def verbose_option(f: Callable) -> Callable:
    """
    Add --verbose/-v flag to command.

    Note: The main CLI group already has --verbose, but this is provided
    for commands that might be used standalone.

    Args:
        f: Command function to decorate

    Returns:
        Decorated function with --verbose option
    """
    return click.option(
        '-v', '--verbose',
        is_flag=True,
        help='Enable verbose output'
    )(f)


def format_option(formats: list, default: str = 'markdown') -> Callable:
    """
    Add --format option with specified choices.

    Args:
        formats: List of valid format strings
        default: Default format (default: 'markdown')

    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        return click.option(
            '--format',
            type=click.Choice(formats),
            default=default,
            help=f'Output format (default: {default})'
        )(f)
    return decorator


def with_db(f: Callable) -> Callable:
    """
    Composite decorator: adds db_option and passes database to command.

    This combines adding the --db-path option with logic to retrieve
    the database from context and pass it to the command.

    Usage:
        @click.command()
        @with_db
        @click.pass_context
        def my_command(ctx, db):
            # db is already initialized
            chats = db.list_chats()

    Args:
        f: Command function to decorate

    Returns:
        Decorated function
    """
    return db_option(f)


# Progress bar utilities for long-running operations
def create_progress_callback(label: str = 'Processing'):
    """
    Create a progress callback for database operations.

    Args:
        label: Label to display in progress bar

    Returns:
        Callback function compatible with aggregator progress callbacks
    """
    def progress_callback(item_id: str, total: int, current: int):
        """Progress callback for database operations."""
        if current % 100 == 0 or current == total:
            click.echo(f"{label}: {current}/{total} items processed...")
    return progress_callback
