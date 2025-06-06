"""
Command-line interface for Cursor Chat Extractor.
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional

from src.extractor import extract_chats, get_cursor_chat_path
from src.parser import parse_chat_json, convert_df_to_markdown, export_to_csv
from src.viewer import list_chat_files, find_chat_file, display_chat_file

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
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert chat data to different formats')
    convert_parser.add_argument('file', help='JSON file to convert')
    convert_parser.add_argument('--format', choices=['csv', 'markdown'], default='csv',
                               help='Output format (default: csv)')
    convert_parser.add_argument('--output-dir', default='chat_exports',
                               help='Output directory for markdown files (default: chat_exports)')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available chat files')
    list_parser.add_argument('--directories', nargs='+', 
                           help='Directories to search (default: ., chat_exports, markdown_chats)')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View a chat file')
    view_parser.add_argument('file', help='Chat file to view')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show information about Cursor installation')
    
    return parser


def extract_command() -> int:
    """
    Handle the extract command.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info("Extracting chats from Cursor database...")
    extracted_files = extract_chats()
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
    if not os.path.exists(args.file):
        logger.error("Error: File %s not found", args.file)
        return 1
    
    try:
        logger.info("Parsing %s...", args.file)
        df = parse_chat_json(args.file)
        
        if args.format == 'csv':
            output_file = os.path.splitext(args.file)[0] + ".csv"
            export_to_csv(df, output_file)
            logger.info("Conversion completed. Output saved to %s", output_file)
        elif args.format == 'markdown':
            if not os.path.exists(args.output_dir):
                os.makedirs(args.output_dir)
            
            files = convert_df_to_markdown(df, args.output_dir)
            logger.info("Conversion completed. %d markdown files created in %s", len(files), args.output_dir)
        
        return 0
    except Exception as e:
        logger.error("Error converting file: %s", str(e))
        return 1


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
    cursor_path = get_cursor_chat_path()
    logger.info("Cursor chat path: %s", cursor_path)
    logger.info("Python: %s", sys.version)
    logger.info("Platform: %s", sys.platform)
    return 0


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
        return extract_command()
    elif args.command == 'convert':
        return convert_command(args)
    elif args.command == 'list':
        return list_command(args)
    elif args.command == 'view':
        return view_command(args)
    elif args.command == 'info':
        return info_command()
    else:
        # No command specified, show help
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
