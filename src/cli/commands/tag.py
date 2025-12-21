"""
CLI commands for tag management.
"""
import click
import logging
from typing import Optional

from ..context import CLIContext
from src.core.db import ChatDatabase
from src.core.config import get_default_db_path
from src.tagger import TagManager
from src.core.tag_registry import TagRegistry

logger = logging.getLogger(__name__)


@click.group()
def tag():
    """Tag management commands."""
    pass


@tag.command()
@click.option('--db-path', type=str, help='Path to database file')
@click.pass_context
def auto_tag_all(ctx, db_path: Optional[str]):
    """
    Auto-tag all existing chats in the database.
    
    This command iterates through all chats and applies tags based on:
    - File extensions from chat_files table
    - Chat mode from chats.mode column
    - Content patterns from messages
    """
    context: CLIContext = ctx.obj
    
    # Get database
    if db_path:
        db = ChatDatabase(db_path)
    else:
        db_path = str(get_default_db_path())
        db = ChatDatabase(db_path)
    
    try:
        tag_manager = TagManager(db=db)
        
        # Get all chats
        logger.info("Fetching all chats from database...")
        all_chats = db.list_chats(limit=100000, offset=0)  # Get all chats
        total_chats = len(all_chats)
        
        if total_chats == 0:
            logger.info("No chats found in database.")
            return
        
        logger.info(f"Found {total_chats} chats. Starting auto-tagging...")
        
        tagged_count = 0
        tags_added = 0
        tag_distribution = {}
        
        for i, chat in enumerate(all_chats, 1):
            chat_id = chat['id']
            
            # Skip if already has tags (optional - comment out to re-tag)
            existing_tags = tag_manager.get_tags(chat_id)
            if existing_tags:
                if context.verbose:
                    logger.debug(f"Chat {chat_id} already has {len(existing_tags)} tags, skipping")
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
                
                if context.verbose:
                    logger.debug(f"Chat {chat_id}: {', '.join(sorted(auto_tags))}")
            
            # Progress update
            if i % 100 == 0:
                logger.info(f"Processed {i}/{total_chats} chats...")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("Auto-tagging complete!")
        logger.info(f"  Total chats processed: {total_chats}")
        logger.info(f"  Chats tagged: {tagged_count}")
        logger.info(f"  Total tags added: {tags_added}")
        
        if tag_distribution:
            logger.info("\nTag distribution (top 20):")
            sorted_tags = sorted(tag_distribution.items(), key=lambda x: -x[1])
            for tag, count in sorted_tags[:20]:
                logger.info(f"  {tag}: {count}")
        
    finally:
        db.close()


@tag.command()
@click.option('--db-path', type=str, help='Path to database file')
@click.pass_context
def list_all(ctx, db_path: Optional[str]):
    """List all tags with their frequency."""
    context: CLIContext = ctx.obj
    
    if db_path:
        db = ChatDatabase(db_path)
    else:
        db = ChatDatabase()
    
    try:
        tag_manager = TagManager(db=db)
        all_tags = tag_manager.get_all_tags()
        
        if not all_tags:
            logger.info("No tags found in database.")
            return
        
        logger.info(f"\nFound {len(all_tags)} unique tags:\n")
        
        # Group by dimension
        tech_tags = {}
        activity_tags = {}
        topic_tags = {}
        other_tags = {}
        
        for tag, count in all_tags.items():
            if tag.startswith('tech/'):
                tech_tags[tag] = count
            elif tag.startswith('activity/'):
                activity_tags[tag] = count
            elif tag.startswith('topic/'):
                topic_tags[tag] = count
            else:
                other_tags[tag] = count
        
        def print_section(title, tags_dict):
            if tags_dict:
                logger.info(f"{title}:")
                sorted_tags = sorted(tags_dict.items(), key=lambda x: -x[1])
                for tag, count in sorted_tags:
                    logger.info(f"  {tag}: {count}")
                logger.info("")
        
        print_section("Tech Tags", tech_tags)
        print_section("Activity Tags", activity_tags)
        print_section("Topic Tags", topic_tags)
        if other_tags:
            print_section("Other Tags", other_tags)
        
    finally:
        db.close()


@tag.command()
@click.argument('chat_id', type=int)
@click.option('--db-path', type=str, help='Path to database file')
@click.pass_context
def show(ctx, chat_id: int, db_path: Optional[str]):
    """Show tags for a specific chat."""
    context: CLIContext = ctx.obj
    
    if db_path:
        db = ChatDatabase(db_path)
    else:
        db = ChatDatabase()
    
    try:
        tag_manager = TagManager(db=db)
        tags = tag_manager.get_tags(chat_id)
        
        if tags:
            logger.info(f"Tags for chat {chat_id}:")
            for tag in sorted(tags):
                logger.info(f"  {tag}")
        else:
            logger.info(f"No tags found for chat {chat_id}")
        
    finally:
        db.close()

