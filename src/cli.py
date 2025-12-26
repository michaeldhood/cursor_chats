"""
Command-line interface for Cursor Chat Extractor.

DEPRECATED: This module is deprecated and will be removed in a future version.
Please use the new Click-based CLI in src/cli/ instead.

The new CLI is now the default. To use this old CLI temporarily, you can
set USE_OLD_CLI=true environment variable (if still supported), but migration
to the new CLI is strongly recommended.
"""
import os
import sys
import argparse
import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from src.extractor import extract_chats
from src.core.config import get_cursor_workspace_storage_path
from src.parser import parse_chat_json, convert_df_to_markdown, export_to_csv
from src.viewer import list_chat_files, find_chat_file, display_chat_file
from src.tagger import TagManager
from src.journal import JournalGenerator, generate_journal_from_file
from src.core.db import ChatDatabase
from src.core.config import get_default_db_path
from src.core.models import ChatMode
from src.services.aggregator import ChatAggregator
from src.services.legacy_importer import LegacyChatImporter
from src.services.search import ChatSearchService
from src.services.exporter import ChatExporter
from src.readers.workspace_reader import WorkspaceStateReader
from src.readers.global_reader import GlobalComposerReader

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for the CLI.
    
    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description='Cursor Chat Extractor - Tools for working with Cursor AI chat logs',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract chat data from Cursor database')
    extract_parser.add_argument('--output-dir', '-o', type=str, default='.',
                               help='Output directory for extracted JSON files (default: current directory)')
    extract_parser.add_argument('--filename-pattern', type=str, 
                               default='chat_data_{workspace}.json',
                               help='Filename pattern for output files. Use {workspace} for workspace ID (default: chat_data_{workspace}.json)')
    extract_parser.add_argument('--all', action='store_true',
                               help='Extract from all workspaces (default behavior, included for consistency)')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert chat data to different formats')
    convert_parser.add_argument('file', nargs='?', help='JSON file to convert (or use --all)')
    convert_parser.add_argument('--format', choices=['csv', 'markdown'], default='csv',
                               help='Output format (default: csv)')
    convert_parser.add_argument('--output-dir', '-o', default='chat_exports',
                               help='Output directory for converted files (default: chat_exports)')
    convert_parser.add_argument('--output-file', type=str,
                               help='Custom output filename (for CSV format only, not used with --all)')
    convert_parser.add_argument('--all', action='store_true',
                               help='Convert all JSON files in current directory')
    convert_parser.add_argument('--pattern', default='chat_data_*.json',
                               help='File pattern for --all flag (default: chat_data_*.json)')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available chat files')
    list_parser.add_argument('--directories', nargs='+', 
                           help='Directories to search (default: ., chat_exports, markdown_chats)')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View a chat file')
    view_parser.add_argument('file', help='Chat file to view')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show information about Cursor installation')
    
    # Ingest command (NEW)
    ingest_parser = subparsers.add_parser('ingest', help='Ingest chats from Cursor databases into local DB')
    ingest_parser.add_argument('--db-path', type=str, 
                              help='Path to database file (default: OS-specific location)')
    ingest_parser.add_argument('--source', choices=['cursor', 'claude', 'all'], default='cursor',
                              help='Source to ingest from: cursor (default), claude, or all')
    ingest_parser.add_argument('--incremental', action='store_true',
                              help='Only ingest chats updated since last run (faster)')
    
    # Watch command (NEW) - daemon mode for automatic ingestion
    watch_parser = subparsers.add_parser('watch', help='Watch for changes and automatically ingest (daemon mode)')
    watch_parser.add_argument('--db-path', type=str,
                             help='Path to database file (default: OS-specific location)')
    watch_parser.add_argument('--source', choices=['cursor', 'claude', 'all'], default='cursor',
                             help='Source to ingest from: cursor (default), claude, or all')
    watch_parser.add_argument('--poll-interval', type=float, default=30.0,
                             help='Polling interval in seconds (default: 30.0, only used if watchdog unavailable)')
    watch_parser.add_argument('--debounce', type=float, default=5.0,
                             help='Debounce time in seconds before triggering ingestion (default: 5.0)')
    watch_parser.add_argument('--use-polling', action='store_true',
                             help='Force use of polling instead of file system events')
    
    # Update-modes command (lightweight mode update without full re-ingest)
    update_modes_parser = subparsers.add_parser('update-modes', help='Update chat modes from Cursor databases (lightweight, no re-ingest)')
    update_modes_parser.add_argument('--db-path', type=str,
                                     help='Path to database file (default: OS-specific location)')
    
    # Import-legacy command (NEW)
    import_parser = subparsers.add_parser('import-legacy', help='Import legacy chat_data_*.json files')
    import_parser.add_argument('path', nargs='?', default='.', 
                              help='Path to directory or file to import (default: current directory)')
    import_parser.add_argument('--pattern', default='chat_data_*.json',
                              help='File pattern for directory import (default: chat_data_*.json)')
    import_parser.add_argument('--db-path', type=str,
                              help='Path to database file (default: OS-specific location)')
    
    # Search command (NEW)
    search_parser = subparsers.add_parser('search', help='Search chats in local database')
    search_parser.add_argument('query', help='Search query (supports FTS5 syntax)')
    search_parser.add_argument('--limit', type=int, default=20,
                              help='Maximum number of results (default: 20)')
    search_parser.add_argument('--db-path', type=str,
                              help='Path to database file (default: OS-specific location)')
    
    # Export command (NEW)
    export_parser = subparsers.add_parser('export', help='Export chats from database')
    export_parser.add_argument('--format', choices=['markdown', 'json'], default='markdown',
                              help='Export format (default: markdown)')
    export_parser.add_argument('--output-dir', '-o', type=str, default='exports',
                              help='Output directory (default: exports)')
    export_parser.add_argument('--chat-id', type=int,
                              help='Export specific chat by ID (otherwise exports all)')
    export_parser.add_argument('--db-path', type=str,
                              help='Path to database file (default: OS-specific location)')
    
    # Export-composer command (NEW) - export raw composer schema
    export_composer_parser = subparsers.add_parser('export-composer', help='Export raw composer data from Cursor database to JSON')
    export_composer_parser.add_argument('composer_id', help='Composer UUID to export')
    export_composer_parser.add_argument('--output', '-o', type=str,
                                       help='Output file path (default: composer_{id}.json)')
    export_composer_parser.add_argument('--include-workspace', action='store_true',
                                       help='Include workspace metadata if available')
    
    # Web UI command (NEW)
    web_parser = subparsers.add_parser('web', help='Start web UI server')
    web_parser.add_argument('--host', default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
    web_parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    web_parser.add_argument('--db-path', type=str,
                           help='Path to database file (default: OS-specific location)')
    
    # Tag command
    tag_parser = subparsers.add_parser('tag', help='Manage tags for chat conversations')
    tag_subparsers = tag_parser.add_subparsers(dest='tag_command', help='Tag operation')
    
    # Tag add subcommand
    tag_add_parser = tag_subparsers.add_parser('add', help='Add tags to a chat')
    tag_add_parser.add_argument('chat_id', help='Chat ID (tabId) to tag')
    tag_add_parser.add_argument('tags', nargs='+', help='Tags to add')
    tag_add_parser.add_argument('--tags-file', default='chat_tags.json', 
                               help='File to store tags (default: chat_tags.json)')
    
    # Tag remove subcommand
    tag_remove_parser = tag_subparsers.add_parser('remove', help='Remove tags from a chat')
    tag_remove_parser.add_argument('chat_id', help='Chat ID to untag')
    tag_remove_parser.add_argument('tags', nargs='+', help='Tags to remove')
    tag_remove_parser.add_argument('--tags-file', default='chat_tags.json',
                                  help='File to store tags (default: chat_tags.json)')
    
    # Tag list subcommand
    tag_list_parser = tag_subparsers.add_parser('list', help='List tags for a chat or all tags')
    tag_list_parser.add_argument('chat_id', nargs='?', help='Chat ID to list tags for (optional)')
    tag_list_parser.add_argument('--all', action='store_true', help='List all tags with counts')
    tag_list_parser.add_argument('--tags-file', default='chat_tags.json',
                                help='File to store tags (default: chat_tags.json)')
    
    # Tag find subcommand
    tag_find_parser = tag_subparsers.add_parser('find', help='Find chats by tag')
    tag_find_parser.add_argument('tag', help='Tag to search for (supports * wildcard)')
    tag_find_parser.add_argument('--tags-file', default='chat_tags.json',
                               help='File to store tags (default: chat_tags.json)')
    
    # Tag auto subcommand
    tag_auto_parser = tag_subparsers.add_parser('auto', help='Auto-tag chats from JSON file')
    tag_auto_parser.add_argument('file', nargs='?', help='JSON file to analyze and tag (or use --all)')
    tag_auto_parser.add_argument('--tags-file', default='chat_tags.json',
                                help='File to store tags (default: chat_tags.json)')
    tag_auto_parser.add_argument('--all', action='store_true',
                                help='Auto-tag all JSON files in current directory')
    tag_auto_parser.add_argument('--pattern', default='chat_data_*.json',
                                help='File pattern for --all flag (default: chat_data_*.json)')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Batch operations: extract, convert, and tag')
    batch_parser.add_argument('--extract', action='store_true', help='Extract chat data')
    batch_parser.add_argument('--convert', action='store_true', help='Convert to specified format')
    batch_parser.add_argument('--tag', action='store_true', help='Auto-tag extracted chats')
    batch_parser.add_argument('--format', choices=['csv', 'markdown'], default='markdown',
                             help='Output format for conversion (default: markdown)')
    batch_parser.add_argument('--output-dir', '-o', default='chat_exports',
                             help='Output directory (default: chat_exports)')
    batch_parser.add_argument('--tags-file', default='chat_tags.json',
                             help='File to store tags (default: chat_tags.json)')
    
    # Journal command
    journal_parser = subparsers.add_parser('journal', help='Generate structured journals from chats')
    journal_subparsers = journal_parser.add_subparsers(dest='journal_command', help='Journal operation')
    
    # Journal generate subcommand
    journal_generate_parser = journal_subparsers.add_parser('generate', help='Generate journal from chat file')
    journal_generate_parser.add_argument('file', help='JSON file to generate journal from')
    journal_generate_parser.add_argument('--template', default='project_journal',
                                        help='Template to use (default: project_journal)')
    journal_generate_parser.add_argument('--format', choices=['markdown', 'html', 'json'], default='markdown',
                                        help='Output format (default: markdown)')
    journal_generate_parser.add_argument('--output', '-o', help='Output file path')
    journal_generate_parser.add_argument('--annotations', help='JSON file with manual annotations')
    
    # Journal template subcommands
    journal_template_parser = journal_subparsers.add_parser('template', help='Manage journal templates')
    journal_template_subparsers = journal_template_parser.add_subparsers(dest='template_command', help='Template operation')
    
    # Template list
    journal_template_list_parser = journal_template_subparsers.add_parser('list', help='List available templates')
    
    # Template show
    journal_template_show_parser = journal_template_subparsers.add_parser('show', help='Show template details')
    journal_template_show_parser.add_argument('name', help='Template name to show')
    
    # Template create
    journal_template_create_parser = journal_template_subparsers.add_parser('create', help='Create custom template')
    journal_template_create_parser.add_argument('name', help='Template name')
    journal_template_create_parser.add_argument('--from-file', help='Create from JSON file')
    
    return parser


def extract_command(args: argparse.Namespace) -> int:
    """
    Handle the extract command.
    
    Args:
        args: Command line arguments
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info("Extracting chats from Cursor database...")
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Created output directory: %s", output_dir)
    
    extracted_files = extract_chats(str(output_dir), args.filename_pattern)
    if extracted_files:
        logger.info("Extraction completed. %d files extracted.", len(extracted_files))
        return 0
    else:
        logger.info("No chat files were extracted.")
        return 1


def convert_command(args: argparse.Namespace) -> int:
    """
    Handle the convert command.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    import glob
    
    # Determine which files to process
    if args.all:
        # Process all files matching pattern
        files_to_process = glob.glob(args.pattern)
        if not files_to_process:
            logger.error("No files found matching pattern: %s", args.pattern)
            return 1
        logger.info("Found %d files to convert", len(files_to_process))
    elif args.file:
        # Process single file
        if not os.path.exists(args.file):
            logger.error("Error: File %s not found", args.file)
            return 1
        files_to_process = [args.file]
    else:
        logger.error("Error: Please specify a file or use --all")
        return 1
    
    # Create output directory if needed
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    success_count = 0
    error_count = 0
    
    for file_path in files_to_process:
        try:
            logger.info("Processing %s...", file_path)
            df = parse_chat_json(file_path)
            
            if args.format == 'csv':
                if args.output_file and len(files_to_process) == 1:
                    # Custom output file only works for single file
                    output_file = os.path.join(args.output_dir, args.output_file)
                else:
                    basename = os.path.basename(os.path.splitext(file_path)[0])
                    output_file = os.path.join(args.output_dir, basename + ".csv")
                
                export_to_csv(df, output_file)
                logger.info("  → Saved CSV to %s", output_file)
                
            elif args.format == 'markdown':
                # For markdown, create subdirectory per workspace
                basename = os.path.basename(os.path.splitext(file_path)[0])
                workspace_dir = os.path.join(args.output_dir, basename)
                if not os.path.exists(workspace_dir):
                    os.makedirs(workspace_dir)
                
                files = convert_df_to_markdown(df, workspace_dir)
                logger.info("  → Created %d markdown files in %s", len(files), workspace_dir)
            
            success_count += 1
            
        except Exception as e:
            logger.error("Error converting %s: %s", file_path, str(e))
            error_count += 1
    
    # Summary
    logger.info("\nConversion summary:")
    logger.info("  Successful: %d", success_count)
    if error_count > 0:
        logger.info("  Failed: %d", error_count)
    
    return 0 if error_count == 0 else 1


def list_command(args: argparse.Namespace) -> int:
    """
    Handle the list command.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    directories = args.directories if args.directories else None
    chat_groups = list_chat_files(directories)
    
    if not chat_groups:
        return 1
    return 0


def view_command(args: argparse.Namespace) -> int:
    """
    Handle the view command.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    filepath = find_chat_file(args.file)
    if filepath:
        if display_chat_file(filepath):
            return 0
    else:
        logger.error("File not found: %s", args.file)
        list_chat_files()
    return 1


def info_command() -> int:
    """
    Handle the info command.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    cursor_path = str(get_cursor_workspace_storage_path())
    logger.info("Cursor chat path: %s", cursor_path)
    logger.info("Python: %s", sys.version)
    logger.info("Platform: %s", sys.platform)
    return 0


def tag_command(args: argparse.Namespace) -> int:
    """
    Handle the tag command and its subcommands.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    tag_manager = TagManager(args.tags_file)
    
    if args.tag_command == 'add':
        tag_manager.add_tags(args.chat_id, args.tags)
        logger.info("Added tags to chat %s: %s", args.chat_id, ', '.join(args.tags))
        return 0
        
    elif args.tag_command == 'remove':
        tag_manager.remove_tags(args.chat_id, args.tags)
        logger.info("Removed tags from chat %s: %s", args.chat_id, ', '.join(args.tags))
        return 0
        
    elif args.tag_command == 'list':
        if args.all:
            # List all tags with counts
            all_tags = tag_manager.get_all_tags()
            if all_tags:
                logger.info("\nAll tags (count):")
                for tag, count in sorted(all_tags.items(), key=lambda x: (-x[1], x[0])):
                    logger.info("  %s (%d)", tag, count)
            else:
                logger.info("No tags found.")
        elif args.chat_id:
            # List tags for specific chat
            tags = tag_manager.get_tags(args.chat_id)
            if tags:
                logger.info("Tags for chat %s: %s", args.chat_id, ', '.join(tags))
            else:
                logger.info("No tags found for chat %s", args.chat_id)
        else:
            logger.error("Please specify a chat ID or use --all")
            return 1
        return 0
        
    elif args.tag_command == 'find':
        chat_ids = tag_manager.find_chats_by_tag(args.tag)
        if chat_ids:
            logger.info("Chats with tag '%s':", args.tag)
            for chat_id in chat_ids:
                logger.info("  %s", chat_id)
        else:
            logger.info("No chats found with tag '%s'", args.tag)
        return 0
        
    elif args.tag_command == 'auto':
        import glob
        
        # Determine which files to process
        if args.all:
            files_to_process = glob.glob(args.pattern)
            if not files_to_process:
                logger.error("No files found matching pattern: %s", args.pattern)
                return 1
            logger.info("Found %d files to auto-tag", len(files_to_process))
        elif args.file:
            if not os.path.exists(args.file):
                logger.error("File not found: %s", args.file)
                return 1
            files_to_process = [args.file]
        else:
            logger.error("Error: Please specify a file or use --all")
            return 1
            
        total_tagged = 0
        error_count = 0
        
        for file_path in files_to_process:
            try:
                logger.info("Auto-tagging chats from %s...", file_path)
                df = parse_chat_json(file_path, tag_manager)
                
                # Get unique chat IDs that were tagged
                tagged_chats = df[df['tags'].apply(len) > 0]['tabId'].unique()
                logger.info("  → Tagged %d chats", len(tagged_chats))
                total_tagged += len(tagged_chats)
                
            except Exception as e:
                logger.error("Error auto-tagging %s: %s", file_path, str(e))
                error_count += 1
        
        # Show summary of all tags
        logger.info("\nAuto-tagging summary:")
        logger.info("  Total chats tagged: %d", total_tagged)
        if error_count > 0:
            logger.info("  Files with errors: %d", error_count)
        
        all_tags = tag_manager.get_all_tags()
        if all_tags:
            logger.info("\nTop tags:")
            for tag, count in sorted(all_tags.items(), key=lambda x: (-x[1], x[0]))[:15]:
                logger.info("  %s (%d)", tag, count)
                
        return 0 if error_count == 0 else 1
    
    else:
        # No subcommand specified
        logger.error("Please specify a tag subcommand (add, remove, list, find, auto)")
        return 1


def batch_command(args: argparse.Namespace) -> int:
    """
    Handle batch operations combining extract, convert, and tag.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    import glob
    
    if not any([args.extract, args.convert, args.tag]):
        # Default to all operations if none specified
        args.extract = args.convert = args.tag = True
    
    extracted_files = []
    
    # Step 1: Extract if requested
    if args.extract:
        logger.info("=== Extracting chat data ===")
        extract_dir = "." if args.convert else args.output_dir
        extracted_files = extract_chats(extract_dir, 'chat_data_{workspace}.json')
        if not extracted_files:
            logger.warning("No files were extracted")
        else:
            logger.info("Extracted %d files", len(extracted_files))
    else:
        # Find existing JSON files
        extracted_files = glob.glob('chat_data_*.json')
    
    if not extracted_files:
        logger.error("No JSON files to process")
        return 1
    
    # Step 2: Convert if requested
    if args.convert:
        logger.info("\n=== Converting to %s format ===", args.format)
        success_count = 0
        
        for file_path in extracted_files:
            try:
                logger.info("Converting %s...", file_path)
                df = parse_chat_json(file_path)
                
                if args.format == 'markdown':
                    # Create subdirectory per workspace
                    basename = os.path.basename(os.path.splitext(file_path)[0])
                    workspace_dir = os.path.join(args.output_dir, basename)
                    if not os.path.exists(workspace_dir):
                        os.makedirs(workspace_dir)
                    
                    files = convert_df_to_markdown(df, workspace_dir)
                    logger.info("  → Created %d markdown files", len(files))
                    
                elif args.format == 'csv':
                    basename = os.path.basename(os.path.splitext(file_path)[0])
                    output_file = os.path.join(args.output_dir, basename + ".csv")
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    
                    export_to_csv(df, output_file)
                    logger.info("  → Saved CSV to %s", output_file)
                
                success_count += 1
                
            except Exception as e:
                logger.error("Error converting %s: %s", file_path, str(e))
        
        logger.info("Converted %d/%d files", success_count, len(extracted_files))
    
    # Step 3: Auto-tag if requested
    if args.tag:
        logger.info("\n=== Auto-tagging chats ===")
        tag_manager = TagManager(args.tags_file)
        total_tagged = 0
        
        for file_path in extracted_files:
            try:
                logger.info("Tagging %s...", file_path)
                df = parse_chat_json(file_path, tag_manager)
                
                tagged_chats = df[df['tags'].apply(len) > 0]['tabId'].unique()
                logger.info("  → Tagged %d chats", len(tagged_chats))
                total_tagged += len(tagged_chats)
                
            except Exception as e:
                logger.error("Error tagging %s: %s", file_path, str(e))
        
        # Show tag summary
        all_tags = tag_manager.get_all_tags()
        if all_tags:
            logger.info("\nTotal chats tagged: %d", total_tagged)
            logger.info("Top tags:")
            for tag, count in sorted(all_tags.items(), key=lambda x: (-x[1], x[0]))[:10]:
                logger.info("  %s (%d)", tag, count)
    
    logger.info("\n=== Batch operation completed ===")
    return 0


def journal_command(args: argparse.Namespace) -> int:
    """
    Handle the journal command and its subcommands.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if args.journal_command == 'generate':
        return journal_generate_command(args)
    elif args.journal_command == 'template':
        return journal_template_command(args)
    else:
        logger.error("Please specify a journal subcommand (generate, template)")
        return 1


def journal_generate_command(args: argparse.Namespace) -> int:
    """Handle journal generate command."""
    if not os.path.exists(args.file):
        logger.error("File not found: %s", args.file)
        return 1
    
    try:
        # Load annotations if provided
        annotations = None
        if args.annotations:
            if os.path.exists(args.annotations):
                with open(args.annotations, 'r') as f:
                    annotations = json.load(f)
            else:
                logger.warning("Annotations file not found: %s", args.annotations)
        
        # Generate journal
        logger.info("Generating journal from %s using template '%s'...", args.file, args.template)
        journal_result = generate_journal_from_file(
            args.file, 
            args.template, 
            annotations, 
            args.format
        )
        
        # Determine output file
        if args.output:
            output_file = args.output
        else:
            basename = os.path.splitext(os.path.basename(args.file))[0]
            ext = 'md' if args.format == 'markdown' else args.format
            output_file = f"journal_{basename}.{ext}"
        
        # Write journal to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(journal_result['content'])
        
        logger.info("Journal generated successfully: %s", output_file)
        logger.info("Template: %s", journal_result['metadata']['template'])
        logger.info("Source chats: %s", journal_result['metadata']['source_chats'])
        
        return 0
        
    except Exception as e:
        logger.error("Error generating journal: %s", str(e))
        return 1


def journal_template_command(args: argparse.Namespace) -> int:
    """Handle journal template subcommands."""
    generator = JournalGenerator()
    
    if args.template_command == 'list':
        templates = generator.list_templates()
        if templates:
            logger.info("Available templates:")
            for template_name in sorted(templates):
                template = generator.get_template(template_name)
                description = template.metadata.get('description', 'No description')
                logger.info("  %s - %s", template_name, description)
        else:
            logger.info("No templates found.")
        return 0
        
    elif args.template_command == 'show':
        template = generator.get_template(args.name)
        if not template:
            logger.error("Template not found: %s", args.name)
            return 1
        
        logger.info("\nTemplate: %s", template.name)
        logger.info("Description: %s", template.metadata.get('description', 'No description'))
        logger.info("Use case: %s", template.metadata.get('use_case', 'General'))
        logger.info("Sections:")
        
        for i, section in enumerate(template.sections, 1):
            logger.info("  %d. %s", i, section['title'].replace('#', '').strip())
            logger.info("     %s", section['prompt'])
        
        return 0
        
    elif args.template_command == 'create':
        if args.from_file:
            if not os.path.exists(args.from_file):
                logger.error("Template file not found: %s", args.from_file)
                return 1
            
            try:
                with open(args.from_file, 'r') as f:
                    template_data = json.load(f)
                
                template = generator.create_custom_template(
                    args.name,
                    template_data['sections'],
                    template_data.get('metadata', {})
                )
                
                logger.info("Created template '%s' from %s", template.name, args.from_file)
                return 0
                
            except Exception as e:
                logger.error("Error creating template: %s", str(e))
                return 1
        else:
            # Interactive template creation
            logger.info("Interactive template creation not yet implemented.")
            logger.info("Please use --from-file option with a JSON template file.")
            return 1
    else:
        logger.error("Please specify a template subcommand (list, show, create)")
        return 1


def ingest_command(args: argparse.Namespace) -> int:
    """
    Handle the ingest command.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    db_path = args.db_path or os.getenv('CURSOR_CHATS_DB_PATH')
    db = ChatDatabase(db_path)
    
    try:
        aggregator = ChatAggregator(db)
        
        total_stats = {"ingested": 0, "skipped": 0, "errors": 0}
        
        # Determine which sources to ingest
        sources_to_ingest = []
        if args.source == "cursor" or args.source == "all":
            sources_to_ingest.append("cursor")
        if args.source == "claude" or args.source == "all":
            sources_to_ingest.append("claude")
        
        # Ingest from each source
        for source in sources_to_ingest:
            if source == "cursor":
                mode_str = "incremental" if args.incremental else "full"
                logger.info("Ingesting chats from Cursor databases (%s mode)...", mode_str)
                
                def progress_callback(composer_id, total, current):
                    if current % 100 == 0 or current == total:
                        logger.info("Progress: %d/%d composers processed...", current, total)
                
                stats = aggregator.ingest_all(progress_callback, incremental=args.incremental)
                
                logger.info("\nCursor ingestion complete!")
                logger.info("  Ingested: %d chats", stats["ingested"])
                logger.info("  Skipped: %d chats", stats["skipped"])
                logger.info("  Errors: %d chats", stats["errors"])
                
                total_stats["ingested"] += stats["ingested"]
                total_stats["skipped"] += stats["skipped"]
                total_stats["errors"] += stats["errors"]
                
            elif source == "claude":
                mode_str = "incremental" if args.incremental else "full"
                logger.info("Ingesting chats from Claude.ai (%s mode)...", mode_str)
                
                def claude_progress_callback(conv_id, total, current):
                    if current % 50 == 0 or current == total:
                        logger.info("Progress: %d/%d conversations processed...", current, total)
                
                stats = aggregator.ingest_claude(claude_progress_callback, incremental=args.incremental)
                
                logger.info("\nClaude.ai ingestion complete!")
                logger.info("  Ingested: %d chats", stats["ingested"])
                logger.info("  Skipped: %d chats", stats["skipped"])
                logger.info("  Errors: %d chats", stats["errors"])
                
                total_stats["ingested"] += stats["ingested"]
                total_stats["skipped"] += stats["skipped"]
                total_stats["errors"] += stats["errors"]
        
        # Summary
        if len(sources_to_ingest) > 1:
            logger.info("\n=== Total Ingestion Summary ===")
            logger.info("  Total ingested: %d chats", total_stats["ingested"])
            logger.info("  Total skipped: %d chats", total_stats["skipped"])
            logger.info("  Total errors: %d chats", total_stats["errors"])
        
        return 0 if total_stats["errors"] == 0 else 1
        
    except Exception as e:
        # Include a traceback to make diagnosing Cursor DB edge cases easier.
        logger.exception("Error during ingestion")
        return 1
    finally:
        db.close()


def watch_command(args: argparse.Namespace) -> int:
    """
    Handle the watch command - daemon mode for automatic ingestion.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    import signal
    
    db_path = args.db_path or os.getenv('CURSOR_CHATS_DB_PATH')
    db = ChatDatabase(db_path)
    
    try:
        aggregator = ChatAggregator(db)
        
        def do_ingestion():
            """Perform incremental ingestion."""
            try:
                sources_to_ingest = []
                if args.source == "cursor" or args.source == "all":
                    sources_to_ingest.append("cursor")
                if args.source == "claude" or args.source == "all":
                    sources_to_ingest.append("claude")
                
                for source in sources_to_ingest:
                    if source == "cursor":
                        stats = aggregator.ingest_all(incremental=True)
                        logger.info("Auto-ingestion: %d ingested, %d skipped, %d errors",
                                   stats["ingested"], stats["skipped"], stats["errors"])
                    elif source == "claude":
                        stats = aggregator.ingest_claude(incremental=True)
                        logger.info("Auto-ingestion: %d ingested, %d skipped, %d errors",
                                   stats["ingested"], stats["skipped"], stats["errors"])
            except Exception as e:
                logger.error("Error during automatic ingestion: %s", e)
        
        # Perform initial ingestion
        logger.info("Performing initial ingestion...")
        do_ingestion()
        
        # Start watcher
        from src.services.watcher import IngestionWatcher
        
        watcher = IngestionWatcher(
            ingestion_callback=do_ingestion,
            use_watchdog=None if not args.use_polling else False,
            debounce_seconds=args.debounce,
            poll_interval=args.poll_interval
        )
        
        # Handle shutdown gracefully
        def signal_handler(sig, frame):
            logger.info("\nShutting down watcher...")
            watcher.stop()
            db.close()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        watcher.start()
        logger.info("Watcher started. Press Ctrl+C to stop.")
        
        # Keep running
        try:
            while watcher.is_running():
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            signal_handler(None, None)
        
        return 0
        
    except Exception as e:
        logger.exception("Error in watch mode")
        return 1
    finally:
        db.close()


def update_modes_command(args: argparse.Namespace) -> int:
    """
    Handle the update-modes command - lightweight mode update without full re-ingest.
    
    This command reads all chats from the database, looks up their correct modes
    from Cursor's databases, and updates only the mode field if it's different.
    Much faster than a full re-ingest since it doesn't re-process messages.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    db_path = args.db_path or os.getenv('CURSOR_CHATS_DB_PATH')
    db = ChatDatabase(db_path)
    
    try:
        logger.info("Updating chat modes from Cursor databases...")
        
        # Get all chats from database
        all_chats = db.list_chats(limit=100000, offset=0)  # Get all chats
        logger.info("Found %d chats in database", len(all_chats))
        
        # Initialize readers
        workspace_reader = WorkspaceStateReader()
        global_reader = GlobalComposerReader()
        
        # Load workspace data to get composer heads
        workspaces_metadata = workspace_reader.read_all_workspaces()
        composer_heads = {}
        for workspace_hash, metadata in workspaces_metadata.items():
            composer_data = metadata.get("composer_data")
            if composer_data and isinstance(composer_data, dict):
                all_composers = composer_data.get("allComposers", [])
                for composer in all_composers:
                    composer_id = composer.get("composerId")
                    if composer_id:
                        composer_heads[composer_id] = {
                            "unifiedMode": composer.get("unifiedMode"),
                            "forceMode": composer.get("forceMode"),
                        }
        
        logger.info("Loaded %d composer heads from workspaces", len(composer_heads))
        
        # Mode mapping
        mode_map = {
            "chat": ChatMode.CHAT,
            "edit": ChatMode.EDIT,
            "agent": ChatMode.AGENT,
            "composer": ChatMode.COMPOSER,
            "plan": ChatMode.PLAN,
            "debug": ChatMode.DEBUG,
            "ask": ChatMode.ASK,
        }
        
        updated_count = 0
        unchanged_count = 0
        not_found_count = 0
        
        # Update each chat's mode
        for chat in all_chats:
            composer_id = chat.get("composer_id")
            current_mode = chat.get("mode", "chat")
            
            # Try to get mode from composer head first
            composer_head = composer_heads.get(composer_id)
            force_mode = None
            unified_mode = None
            
            if composer_head:
                force_mode = composer_head.get("forceMode")
                unified_mode = composer_head.get("unifiedMode")
            
            # If not in workspace head, try global database
            if not force_mode and not unified_mode:
                composer_data = global_reader.read_composer(composer_id)
                if composer_data and composer_data.get("data"):
                    data = composer_data["data"]
                    force_mode = data.get("forceMode")
                    unified_mode = data.get("unifiedMode")
            
            # Determine correct mode
            correct_mode_str = force_mode or unified_mode or "chat"
            correct_mode = mode_map.get(correct_mode_str, ChatMode.CHAT)
            
            # Update if different
            if current_mode != correct_mode.value:
                cursor = db.conn.cursor()
                cursor.execute("UPDATE chats SET mode = ? WHERE id = ?", 
                             (correct_mode.value, chat["id"]))
                db.conn.commit()
                updated_count += 1
                if updated_count % 10 == 0:
                    logger.info("Updated %d chats...", updated_count)
            else:
                unchanged_count += 1
        
        logger.info("\nMode update complete!")
        logger.info("  Updated: %d chats", updated_count)
        logger.info("  Unchanged: %d chats", unchanged_count)
        logger.info("  Not found in Cursor: %d chats", not_found_count)
        
        return 0
    except Exception as e:
        logger.error("Error updating modes: %s", e, exc_info=True)
        return 1
    finally:
        db.close()


def import_legacy_command(args: argparse.Namespace) -> int:
    """
    Handle the import-legacy command.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info("Importing legacy chat files...")
    
    db_path = args.db_path or os.getenv('CURSOR_CHATS_DB_PATH')
    db = ChatDatabase(db_path)
    
    try:
        importer = LegacyChatImporter(db)
        path = Path(args.path)
        
        if path.is_file():
            # Import single file
            count = importer.import_file(path)
            logger.info("Imported %d chats from %s", count, path)
        else:
            # Import directory
            stats = importer.import_directory(path, args.pattern)
            logger.info("\nImport complete!")
            logger.info("  Files processed: %d", stats["files"])
            logger.info("  Chats imported: %d", stats["chats"])
            logger.info("  Errors: %d", stats["errors"])
            count = stats["chats"]
        
        return 0 if count > 0 else 1
        
    except Exception as e:
        logger.error("Error during import: %s", e)
        return 1
    finally:
        db.close()


def search_command(args: argparse.Namespace) -> int:
    """
    Handle the search command.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    db_path = args.db_path or os.getenv('CURSOR_CHATS_DB_PATH')
    db = ChatDatabase(db_path)
    
    try:
        search_service = ChatSearchService(db)
        results = search_service.search(args.query, args.limit)
        
        if not results:
            logger.info("No chats found matching '%s'", args.query)
            return 1
        
        logger.info("Found %d chats matching '%s':\n", len(results), args.query)
        
        for chat in results:
            logger.info("Chat ID: %d", chat['id'])
            logger.info("  Title: %s", chat['title'])
            logger.info("  Mode: %s", chat['mode'])
            logger.info("  Created: %s", chat['created_at'])
            if chat.get('workspace_path'):
                logger.info("  Workspace: %s", chat['workspace_path'])
            logger.info("")
        
        return 0
        
    except Exception as e:
        logger.error("Error during search: %s", e)
        return 1
    finally:
        db.close()


def web_command(args: argparse.Namespace) -> int:
    """
    Handle the web command - start Flask server with gevent for SSE support.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if args.db_path:
        os.environ['CURSOR_CHATS_DB_PATH'] = args.db_path
    
    # Monkey patch for gevent async support (required for SSE)
    try:
        from gevent import monkey
        monkey.patch_all()
        from gevent.pywsgi import WSGIServer
    except ImportError:
        logger.error("gevent is required for SSE support. Install with: pip install gevent")
        logger.info("Falling back to standard Flask server (SSE may not work properly)")
        from src.ui.web.app import app
        app.run(host=args.host, port=args.port, debug=True)
        return 0
    
    from src.ui.web.app import app
    
    logger.info("Starting web UI server on http://%s:%d", args.host, args.port)
    logger.info("SSE enabled - frontend will auto-update when new chats are ingested")
    logger.info("Press Ctrl+C to stop")
    
    server = WSGIServer((args.host, args.port), app)
    server.serve_forever()
    return 0


def export_command(args: argparse.Namespace) -> int:
    """
    Handle the export command.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info("Exporting chats...")
    
    db_path = args.db_path or os.getenv('CURSOR_CHATS_DB_PATH')
    db = ChatDatabase(db_path)
    
    try:
        exporter = ChatExporter(db)
        output_dir = Path(args.output_dir)
        
        if args.chat_id:
            # Export single chat
            output_path = output_dir / f"chat_{args.chat_id}.md"
            if exporter.export_chat_markdown(args.chat_id, output_path):
                logger.info("Exported chat %d to %s", args.chat_id, output_path)
                return 0
            else:
                return 1
        else:
            # Export all chats
            if args.format == 'markdown':
                count = exporter.export_all_markdown(output_dir)
                logger.info("Exported %d chats to %s", count, output_dir)
                return 0 if count > 0 else 1
            else:
                logger.error("JSON export not yet implemented")
                return 1
        
    except Exception as e:
        logger.error("Error during export: %s", e)
        return 1
    finally:
        db.close()


def export_composer_command(args: argparse.Namespace) -> int:
    """
    Handle the export-composer command - export raw composer schema to JSON.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    composer_id = args.composer_id
    logger.info("Exporting composer %s...", composer_id)
    
    try:
        from src.readers.global_reader import GlobalComposerReader
        from src.readers.workspace_reader import WorkspaceStateReader
        
        # Read composer data from global database
        global_reader = GlobalComposerReader()
        composer_info = global_reader.read_composer(composer_id)
        
        if not composer_info:
            logger.error("Composer %s not found in global database", composer_id)
            return 1
        
        composer_data = composer_info["data"]
        
        # Resolve conversation bubbles if using headers-only format
        conversation = composer_data.get("conversation", [])
        if not conversation:
            headers = composer_data.get("fullConversationHeadersOnly", [])
            if headers:
                logger.info("Resolving conversation bubbles from headers...")
                from src.services.aggregator import ChatAggregator
                from src.core.db import ChatDatabase
                # Create a temporary aggregator just to use the resolution method
                temp_db = ChatDatabase(":memory:")  # In-memory DB just for method access
                temp_aggregator = ChatAggregator(temp_db)
                conversation = temp_aggregator._resolve_conversation_from_headers(composer_id, headers)
                temp_db.close()
                # Add resolved conversation to export data
                composer_data = composer_data.copy()
                composer_data["conversation_resolved"] = conversation
                logger.info("Resolved %d conversation bubbles", len(conversation))
        
        export_data = {
            "composer_id": composer_id,
            "source": "cursor_global_database",
            "exported_at": datetime.now().isoformat(),
            "composer_data": composer_data,
        }
        
        # Optionally include workspace metadata
        if args.include_workspace:
            logger.info("Looking up workspace metadata...")
            workspace_reader = WorkspaceStateReader()
            workspaces = workspace_reader.read_all_workspaces()
            
            workspace_info = None
            for workspace_hash, metadata in workspaces.items():
                composer_data = metadata.get("composer_data")
                if composer_data and isinstance(composer_data, dict):
                    all_composers = composer_data.get("allComposers", [])
                    for composer in all_composers:
                        if composer.get("composerId") == composer_id:
                            workspace_info = {
                                "workspace_hash": workspace_hash,
                                "workspace_metadata": {
                                    "project_path": metadata.get("project_path"),
                                    "composer_head": {
                                        "name": composer.get("name"),
                                        "subtitle": composer.get("subtitle"),
                                        "createdAt": composer.get("createdAt"),
                                        "lastUpdatedAt": composer.get("lastUpdatedAt"),
                                        "unifiedMode": composer.get("unifiedMode"),
                                        "forceMode": composer.get("forceMode"),
                                    }
                                }
                            }
                            break
                    if workspace_info:
                        break
            
            if workspace_info:
                export_data["workspace_info"] = workspace_info
                logger.info("Found workspace metadata for workspace %s", workspace_info["workspace_hash"])
            else:
                logger.info("No workspace metadata found for this composer")
        
        # Determine output file
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = Path(f"composer_{composer_id}.json")
        
        # Write JSON file with pretty formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info("Exported composer to %s", output_path)
        logger.info("  File size: %d bytes", output_path.stat().st_size)
        
        # Print summary
        final_composer_data = export_data["composer_data"]
        logger.info("\nComposer Summary:")
        logger.info("  ID: %s", composer_id)
        logger.info("  Name: %s", final_composer_data.get("name") or final_composer_data.get("subtitle") or "Untitled")
        logger.info("  Created: %s", final_composer_data.get("createdAt"))
        logger.info("  Updated: %s", final_composer_data.get("lastUpdatedAt"))
        logger.info("  Mode: %s", final_composer_data.get("forceMode") or final_composer_data.get("unifiedMode") or "chat")
        
        conversation = final_composer_data.get("conversation", []) or final_composer_data.get("conversation_resolved", [])
        headers = final_composer_data.get("fullConversationHeadersOnly", [])
        logger.info("  Messages: %d bubbles", len(conversation) if conversation else len(headers))
        
        return 0
        
    except Exception as e:
        logger.exception("Error exporting composer: %s", e)
        return 1


def main() -> int:
    """
    Main entry point for the CLI.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format='%(message)s')
    
    if args.command == 'extract':
        return extract_command(args)
    elif args.command == 'convert':
        return convert_command(args)
    elif args.command == 'list':
        return list_command(args)
    elif args.command == 'view':
        return view_command(args)
    elif args.command == 'info':
        return info_command()
    elif args.command == 'tag':
        return tag_command(args)
    elif args.command == 'batch':
        return batch_command(args)
    elif args.command == 'journal':
        return journal_command(args)
    elif args.command == 'ingest':
        return ingest_command(args)
    elif args.command == 'watch':
        return watch_command(args)
    elif args.command == 'update-modes':
        return update_modes_command(args)
    elif args.command == 'import-legacy':
        return import_legacy_command(args)
    elif args.command == 'search':
        return search_command(args)
    elif args.command == 'export':
        return export_command(args)
    elif args.command == 'web':
        return web_command(args)
    elif args.command == 'export-composer':
        return export_composer_command(args)
    else:
        # No command specified, show help
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
