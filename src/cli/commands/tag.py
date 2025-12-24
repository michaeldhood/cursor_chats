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
    try:
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
            try:
                chat_id = chat['id']
                
                # Ensure chat_id is an integer
                if not isinstance(chat_id, int):
                    if ctx.obj.verbose:
                        click.echo(f"Warning: Chat has non-integer ID: {chat_id} (type: {type(chat_id)}), skipping", err=True)
                    continue

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
                try:
                    chat_detail = db.get_chat(chat_id)
                except Exception as get_chat_e:
                    raise
                
                if not chat_detail:
                    continue

                try:
                    messages = chat_detail.get('messages', [])
                    content_parts = []
                    for msg_idx, msg in enumerate(messages):
                        text = msg.get('text', '') or msg.get('rich_text', '')
                        if text:
                            content_parts.append(text)

                    content = ' '.join(content_parts)
                except Exception as msg_e:
                    raise

                # Auto-tag
                try:
                    auto_tags = tag_manager.auto_tag(
                        content=content,
                        file_extensions=file_extensions if file_extensions else None,
                        chat_mode=chat_mode
                    )
                except Exception as auto_tag_e:
                    raise

                if auto_tags:
                    # Use list comprehension instead of list() constructor
                    # Workaround: Click appears to intercept list() constructor calls
                    # when used with sets containing strings, causing argument parsing errors
                    auto_tags_list = [tag for tag in auto_tags]
                    
                    tag_manager.add_tags(chat_id, auto_tags_list)
                    tagged_count += 1
                    tags_added += len(auto_tags)

                    # Track distribution
                    for tag in auto_tags:
                        tag_distribution[tag] = tag_distribution.get(tag, 0) + 1

                    if ctx.obj.verbose:
                        click.echo(f"Chat {chat_id}: {', '.join(sorted(auto_tags))}", err=True)
            except Exception as e:
                click.echo(f"Error processing chat {chat.get('id', 'unknown')}: {e}", err=True)
                if ctx.obj.verbose:
                    import traceback
                    click.echo(traceback.format_exc(), err=True)
                continue

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
    except click.ClickException as e:
        raise
    except Exception as e:
        import traceback
        click.secho(f"Unexpected error: {e}", fg='red', err=True)
        if ctx.obj.verbose:
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()

