"""
Tag management CLI commands.

Commands for adding, removing, listing, finding, and auto-tagging chat conversations.
Uses the database-based TagManager with registry-based tag resolution.
"""
import click
from pathlib import Path

from ..common import db_option
from src.tagger import TagManager


@click.group()
def tag():
    """Manage tags for chat conversations."""
    pass


@tag.command()
@click.argument('chat_id', type=int)
@click.argument('tags', nargs=-1, required=True)
@db_option
@click.pass_context
def add(ctx, chat_id, tags, db_path):
    """Add tags to a chat."""
    if db_path:
        ctx.obj.db_path = Path(db_path)

    db = ctx.obj.get_db()
    tag_manager = TagManager(db=db)
    tag_manager.add_tags(chat_id, list(tags))
    click.secho(f"Added tags to chat {chat_id}: {', '.join(tags)}", fg='green')


@tag.command()
@click.argument('chat_id', type=int)
@click.argument('tags', nargs=-1, required=True)
@db_option
@click.pass_context
def remove(ctx, chat_id, tags, db_path):
    """Remove tags from a chat."""
    if db_path:
        ctx.obj.db_path = Path(db_path)

    db = ctx.obj.get_db()
    tag_manager = TagManager(db=db)
    tag_manager.remove_tags(chat_id, list(tags))
    click.secho(f"Removed tags from chat {chat_id}: {', '.join(tags)}", fg='green')


@tag.command()
@click.argument('chat_id', type=int, required=False)
@click.option('--all', is_flag=True, help='List all tags with counts')
@db_option
@click.pass_context
def list(ctx, chat_id, all, db_path):
    """List tags for a chat or all tags."""
    if db_path:
        ctx.obj.db_path = Path(db_path)

    db = ctx.obj.get_db()
    tag_manager = TagManager(db=db)

    if all:
        # List all tags with counts
        all_tags = tag_manager.get_all_tags()
        if all_tags:
            click.echo("\nAll tags (count):")
            # Group by dimension
            tech_tags = {t: c for t, c in all_tags.items() if t.startswith('tech/')}
            activity_tags = {t: c for t, c in all_tags.items() if t.startswith('activity/')}
            topic_tags = {t: c for t, c in all_tags.items() if t.startswith('topic/')}
            other_tags = {t: c for t, c in all_tags.items()
                          if not (t.startswith('tech/') or t.startswith('activity/') or t.startswith('topic/'))}

            def print_section(title, tags_dict):
                if tags_dict:
                    click.echo(f"\n{title}:")
                    for tag_name, count in sorted(tags_dict.items(), key=lambda x: (-x[1], x[0])):
                        click.echo(f"  {tag_name} ({count})")

            print_section("Tech Tags", tech_tags)
            print_section("Activity Tags", activity_tags)
            print_section("Topic Tags", topic_tags)
            print_section("Other Tags", other_tags)
        else:
            click.echo("No tags found.")
    elif chat_id:
        # List tags for specific chat
        tags = tag_manager.get_tags(chat_id)
        if tags:
            click.echo(f"Tags for chat {chat_id}: {', '.join(sorted(tags))}")
        else:
            click.echo(f"No tags found for chat {chat_id}")
    else:
        click.secho("Error: Please specify a chat ID or use --all", fg='red', err=True)
        raise click.Abort()


@tag.command()
@click.argument('tag_name', metavar='TAG')
@db_option
@click.pass_context
def find(ctx, tag_name, db_path):
    """Find chats by tag (supports * wildcard)."""
    if db_path:
        ctx.obj.db_path = Path(db_path)

    db = ctx.obj.get_db()
    tag_manager = TagManager(db=db)
    chat_ids = tag_manager.find_chats_by_tag(tag_name)

    if chat_ids:
        click.secho(f"\nFound {len(chat_ids)} chats with tag '{tag_name}':", fg='green')
        for chat_id in chat_ids:
            click.echo(f"  Chat ID: {chat_id}")
    else:
        click.echo(f"No chats found with tag '{tag_name}'")


@tag.command('auto-tag-all')
@db_option
@click.pass_context
def auto_tag_all(ctx, db_path):
    """
    Auto-tag all existing chats in the database.

    This command iterates through all chats and applies tags based on:
    - File extensions from chat_files table
    - Chat mode from chats.mode column
    - Content patterns from messages
    """
    if db_path:
        ctx.obj.db_path = Path(db_path)

    db = ctx.obj.get_db()
    tag_manager = TagManager(db=db)

    # Get all chats
    click.echo("Fetching all chats from database...")
    all_chats = db.list_chats(limit=100000, offset=0)  # Get all chats
    total_chats = len(all_chats)

    if total_chats == 0:
        click.echo("No chats found in database.")
        return

    click.echo(f"Found {total_chats} chats. Starting auto-tagging...")

    tagged_count = 0
    tags_added = 0
    tag_distribution = {}

    for i, chat in enumerate(all_chats, 1):
        chat_id = chat['id']

        # Skip if already has tags (optional - comment out to re-tag)
        existing_tags = tag_manager.get_tags(chat_id)
        if existing_tags:
            if ctx.obj.verbose:
                click.echo(f"Chat {chat_id} already has {len(existing_tags)} tags, skipping", err=True)
            continue

        # Get chat metadata
        chat_mode = chat.get('mode')

        # Get file extensions
        file_paths = db.get_chat_files(chat_id)
        file_extensions = []
        for path in file_paths:
            if '.' in path:
                ext = '.' + path.split('.')[-1]
                file_extensions.append(ext)

        # Get message content
        chat_detail = db.get_chat(chat_id)
        if not chat_detail:
            continue

        messages = chat_detail.get('messages', [])
        content_parts = []
        for msg in messages:
            text = msg.get('text', '') or msg.get('rich_text', '')
            if text:
                content_parts.append(text)

        content = ' '.join(content_parts)

        # Auto-tag
        auto_tags = tag_manager.auto_tag(
            content=content,
            file_extensions=file_extensions if file_extensions else None,
            chat_mode=chat_mode
        )

        if auto_tags:
            tag_manager.add_tags(chat_id, list(auto_tags))
            tagged_count += 1
            tags_added += len(auto_tags)

            # Track distribution
            for tag in auto_tags:
                tag_distribution[tag] = tag_distribution.get(tag, 0) + 1

            if ctx.obj.verbose:
                click.echo(f"Chat {chat_id}: {', '.join(sorted(auto_tags))}", err=True)

        # Progress update
        if i % 100 == 0:
            click.echo(f"Progress: {i}/{total_chats} chats processed...")

    # Summary
    click.echo("\n" + "="*60)
    click.secho("Auto-tagging complete!", fg='green')
    click.echo(f"  Total chats processed: {total_chats}")
    click.echo(f"  Chats tagged: {tagged_count}")
    click.echo(f"  Total tags added: {tags_added}")

    if tag_distribution:
        click.echo("\nTag distribution (top 20):")
        sorted_tags = sorted(tag_distribution.items(), key=lambda x: -x[1])
        for tag, count in sorted_tags[:20]:
            click.echo(f"  {tag}: {count}")

