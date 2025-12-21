"""
Miscellaneous CLI commands (info, list, view).

Simple utility commands for inspecting the Cursor installation and
browsing exported chat files.
"""
import click
import sys

from src.core.config import get_cursor_workspace_storage_path
from src.viewer import list_chat_files, find_chat_file, display_chat_file


@click.command()
def info():
    """Show information about Cursor installation."""
    cursor_path = str(get_cursor_workspace_storage_path())
    click.echo(f"Cursor chat path: {cursor_path}")
    click.echo(f"Python: {sys.version}")
    click.echo(f"Platform: {sys.platform}")


@click.command()
@click.option(
    '--directories',
    multiple=True,
    help='Directories to search (default: ., chat_exports, markdown_chats)'
)
def list(directories):
    """List available chat files."""
    # Convert tuple to list (or None if empty)
    dirs = list(directories) if directories else None
    chat_groups = list_chat_files(dirs)

    if not chat_groups:
        raise click.Abort()


@click.command()
@click.argument('file')
def view(file):
    """View a chat file."""
    filepath = find_chat_file(file)
    if filepath:
        if not display_chat_file(filepath):
            raise click.Abort()
    else:
        click.secho(f"File not found: {file}", fg='red', err=True)
        click.echo("\nAvailable files:")
        list_chat_files()
        raise click.Abort()
