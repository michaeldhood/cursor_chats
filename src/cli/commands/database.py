"""
Database-related CLI commands.

Commands for ingesting, searching, importing, and exporting chat data
from the local database.
"""
import click
from pathlib import Path

from src.core.db import ChatDatabase
from src.core.config import get_default_db_path
from src.services.legacy_importer import LegacyChatImporter
from src.services.search import ChatSearchService
from src.services.exporter import ChatExporter
from src.cli.common import db_option, output_dir_option, format_option, create_progress_callback
from src.cli.orchestrators.ingestion import IngestionOrchestrator


@click.command()
@db_option
@click.option(
    '--source',
    type=click.Choice(['cursor', 'claude', 'all']),
    default='cursor',
    help='Source to ingest from'
)
@click.option(
    '--incremental',
    is_flag=True,
    help='Only ingest chats updated since last run (faster)'
)
@click.pass_context
def ingest(ctx, db_path, source, incremental):
    """Ingest chats from Cursor databases into local DB."""
    # Get database from context
    if db_path:
        ctx.obj.db_path = Path(db_path)

    db = ctx.obj.get_db()

    try:
        orchestrator = IngestionOrchestrator(db)

        # Create progress callback
        def progress_callback(item_id, total, current):
            if current % 100 == 0 or current == total:
                click.echo(f"Progress: {current}/{total} items processed...")

        mode_str = "incremental" if incremental else "full"
        click.echo(f"Ingesting chats from {source} ({mode_str} mode)...")

        stats = orchestrator.ingest(source, incremental, progress_callback)

        # Display results
        click.echo(f"\nIngestion complete!")
        click.secho(f"  Ingested: {stats['ingested']} chats", fg='green')
        click.echo(f"  Skipped: {stats['skipped']} chats")
        if stats['errors'] > 0:
            click.secho(f"  Errors: {stats['errors']} chats", fg='yellow')
            raise click.Abort()

    except Exception as e:
        click.secho(f"Error during ingestion: {e}", fg='red', err=True)
        if ctx.obj.verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@click.command('import-legacy')
@click.argument('path', default='.', type=click.Path(exists=True))
@click.option(
    '--pattern',
    default='chat_data_*.json',
    help='File pattern for directory import'
)
@db_option
@click.pass_context
def import_legacy(ctx, path, pattern, db_path):
    """Import legacy chat_data_*.json files."""
    click.echo("Importing legacy chat files...")

    # Get database from context
    if db_path:
        ctx.obj.db_path = Path(db_path)

    db = ctx.obj.get_db()

    try:
        importer = LegacyChatImporter(db)
        path_obj = Path(path)

        if path_obj.is_file():
            # Import single file
            count = importer.import_file(path_obj)
            click.secho(f"Imported {count} chats from {path}", fg='green')
        else:
            # Import directory
            stats = importer.import_directory(path_obj, pattern)
            click.echo("\nImport complete!")
            click.echo(f"  Files processed: {stats['files']}")
            click.secho(f"  Chats imported: {stats['chats']}", fg='green')
            if stats['errors'] > 0:
                click.secho(f"  Errors: {stats['errors']}", fg='yellow')

        if not (count if path_obj.is_file() else stats['chats']):
            raise click.Abort()

    except Exception as e:
        click.secho(f"Error during import: {e}", fg='red', err=True)
        raise click.Abort()


@click.command()
@click.argument('query', required=False)
@click.option(
    '--limit',
    default=20,
    help='Maximum number of results'
)
@click.option(
    '--tag', '-t',
    multiple=True,
    help='Filter by tag(s). Can be specified multiple times. Supports wildcards (e.g., "tech/%").'
)
@click.option(
    '--list-tags',
    is_flag=True,
    help='List all available tags with counts'
)
@db_option
@click.pass_context
def search(ctx, query, limit, tag, list_tags, db_path):
    """Search chats in local database.
    
    Use QUERY for full-text search, or --tag to filter by tags.
    
    Examples:
    
      python -m src search "python error"     # Full-text search
      
      python -m src search --tag tech/python  # Filter by tag
      
      python -m src search --tag "tech/%"     # All tech tags (wildcard)
      
      python -m src search --list-tags        # Show all tags
    """
    # Get database from context
    if db_path:
        ctx.obj.db_path = Path(db_path)

    db = ctx.obj.get_db()

    try:
        # List all tags mode
        if list_tags:
            all_tags = db.get_all_tags()
            if all_tags:
                click.secho("\nAll tags (by count):\n", fg='green')
                
                # Group by dimension
                tech_tags = {t: c for t, c in all_tags.items() if t.startswith('tech/')}
                activity_tags = {t: c for t, c in all_tags.items() if t.startswith('activity/')}
                topic_tags = {t: c for t, c in all_tags.items() if t.startswith('topic/')}
                other_tags = {t: c for t, c in all_tags.items() 
                            if not t.startswith(('tech/', 'activity/', 'topic/'))}
                
                def print_section(title, tags_dict):
                    if tags_dict:
                        click.secho(f"  {title}:", fg='cyan')
                        for tag_name, count in sorted(tags_dict.items(), key=lambda x: (-x[1], x[0])):
                            click.echo(f"    {tag_name} ({count})")
                        click.echo()
                
                print_section("Tech Tags", tech_tags)
                print_section("Activity Tags", activity_tags)
                print_section("Topic Tags", topic_tags)
                print_section("Other Tags", other_tags)
            else:
                click.echo("No tags found. Run 'python -m src tag auto-tag-all' to auto-tag chats.")
            return
        
        search_service = ChatSearchService(db)
        
        # Tag filtering mode
        if tag:
            tags_list = list(tag)
            results = search_service.list_chats(limit=limit, tags_filter=tags_list)
            total = search_service.count_chats(tags_filter=tags_list)
            
            if not results:
                click.echo(f"No chats found with tag(s): {', '.join(tags_list)}")
                raise click.Abort()
            
            tag_desc = ', '.join(tags_list)
            click.secho(f"\nFound {total} chats with tag(s) '{tag_desc}' (showing {len(results)}):\n", fg='green')
            
            for chat in results:
                click.echo(f"Chat ID: {chat['id']}")
                click.echo(f"  Title: {chat['title']}")
                click.echo(f"  Mode: {chat['mode']}")
                click.echo(f"  Created: {chat['created_at']}")
                if chat.get('tags'):
                    click.echo(f"  Tags: {', '.join(chat['tags'][:5])}")
                if chat.get('workspace_path'):
                    click.echo(f"  Workspace: {chat['workspace_path']}")
                click.echo()
            return
        
        # Full-text search mode
        if not query:
            click.echo("Please provide a search query or use --tag to filter by tags.")
            click.echo("Use --list-tags to see available tags.")
            raise click.Abort()
        
        results = search_service.search(query, limit)

        if not results:
            click.echo(f"No chats found matching '{query}'")
            raise click.Abort()

        click.secho(f"\nFound {len(results)} chats matching '{query}':\n", fg='green')

        for chat in results:
            click.echo(f"Chat ID: {chat['id']}")
            click.echo(f"  Title: {chat['title']}")
            click.echo(f"  Mode: {chat['mode']}")
            click.echo(f"  Created: {chat['created_at']}")
            if chat.get('tags'):
                click.echo(f"  Tags: {', '.join(chat['tags'][:5])}")
            if chat.get('workspace_path'):
                click.echo(f"  Workspace: {chat['workspace_path']}")
            click.echo()

    except click.Abort:
        raise
    except Exception as e:
        click.secho(f"Error during search: {e}", fg='red', err=True)
        raise click.Abort()


@click.command()
@format_option(['markdown', 'json'], default='markdown')
@output_dir_option(default='exports')
@click.option(
    '--chat-id',
    type=int,
    help='Export specific chat by ID (otherwise exports all)'
)
@db_option
@click.pass_context
def export(ctx, format, output_dir, chat_id, db_path):
    """Export chats from database."""
    click.echo("Exporting chats...")

    # Get database from context
    if db_path:
        ctx.obj.db_path = Path(db_path)

    db = ctx.obj.get_db()

    try:
        exporter = ChatExporter(db)
        output_path = Path(output_dir)

        if chat_id:
            # Export single chat
            chat_file = output_path / f"chat_{chat_id}.md"
            if exporter.export_chat_markdown(chat_id, chat_file):
                click.secho(f"Exported chat {chat_id} to {chat_file}", fg='green')
            else:
                raise click.Abort()
        else:
            # Export all chats
            if format == 'markdown':
                count = exporter.export_all_markdown(output_path)
                click.secho(f"Exported {count} chats to {output_path}", fg='green')
                if count == 0:
                    raise click.Abort()
            else:
                click.secho("JSON export not yet implemented", fg='yellow')
                raise click.Abort()

    except Exception as e:
        click.secho(f"Error during export: {e}", fg='red', err=True)
        raise click.Abort()
