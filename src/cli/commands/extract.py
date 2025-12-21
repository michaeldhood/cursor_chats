"""
Extract and convert CLI commands.

Commands for extracting chat data from Cursor databases and converting
between different formats (JSON, CSV, Markdown).
"""
import click
import os
import glob
from pathlib import Path

from src.extractor import extract_chats
from src.parser import parse_chat_json, convert_df_to_markdown, export_to_csv
from src.cli.common import output_dir_option, format_option


@click.command()
@output_dir_option(default='.')
@click.option(
    '--filename-pattern',
    default='chat_data_{workspace}.json',
    help='Filename pattern. Use {workspace} for workspace ID'
)
@click.option(
    '--all',
    is_flag=True,
    help='Extract from all workspaces (default behavior)'
)
def extract(output_dir, filename_pattern, all):
    """Extract chat data from Cursor database."""
    click.echo("Extracting chats from Cursor database...")

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if not output_path.exists():
        click.echo(f"Created output directory: {output_path}")

    extracted_files = extract_chats(str(output_path), filename_pattern)

    if extracted_files:
        click.secho(
            f"✓ Extraction completed. {len(extracted_files)} files extracted.",
            fg='green'
        )
    else:
        click.echo("No chat files were extracted.")
        raise click.Abort()


@click.command()
@click.argument('file', required=False)
@format_option(['csv', 'markdown'], default='csv')
@output_dir_option(default='chat_exports')
@click.option(
    '--output-file',
    help='Custom output filename (CSV only, single file only)'
)
@click.option(
    '--all',
    is_flag=True,
    help='Convert all JSON files in current directory'
)
@click.option(
    '--pattern',
    default='chat_data_*.json',
    help='File pattern for --all flag'
)
def convert(file, format, output_dir, output_file, all, pattern):
    """Convert chat data to different formats."""
    # Determine which files to process
    if all:
        files_to_process = glob.glob(pattern)
        if not files_to_process:
            click.secho(f"No files found matching pattern: {pattern}", fg='red', err=True)
            raise click.Abort()
        click.echo(f"Found {len(files_to_process)} files to convert")
    elif file:
        if not os.path.exists(file):
            click.secho(f"Error: File {file} not found", fg='red', err=True)
            raise click.Abort()
        files_to_process = [file]
    else:
        click.secho("Error: Please specify a file or use --all", fg='red', err=True)
        raise click.Abort()

    # Create output directory if needed
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    success_count = 0
    error_count = 0

    for file_path in files_to_process:
        try:
            click.echo(f"Processing {file_path}...")
            df = parse_chat_json(file_path)

            if format == 'csv':
                if output_file and len(files_to_process) == 1:
                    # Custom output file only works for single file
                    output_path = os.path.join(output_dir, output_file)
                else:
                    basename = os.path.basename(os.path.splitext(file_path)[0])
                    output_path = os.path.join(output_dir, basename + ".csv")

                export_to_csv(df, output_path)
                click.echo(f"  → Saved CSV to {output_path}")

            elif format == 'markdown':
                # For markdown, create subdirectory per workspace
                basename = os.path.basename(os.path.splitext(file_path)[0])
                workspace_dir = os.path.join(output_dir, basename)
                os.makedirs(workspace_dir, exist_ok=True)

                files = convert_df_to_markdown(df, workspace_dir)
                click.echo(f"  → Created {len(files)} markdown files in {workspace_dir}")

            success_count += 1

        except Exception as e:
            click.secho(f"Error converting {file_path}: {e}", fg='red', err=True)
            error_count += 1

    # Summary
    click.echo("\nConversion summary:")
    click.echo(f"  Successful: {success_count}")
    if error_count > 0:
        click.secho(f"  Failed: {error_count}", fg='yellow')
        raise click.Abort()
