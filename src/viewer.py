"""
Module for listing and viewing Cursor chat files.
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def find_chat_files(directories: List[str] = None) -> List[str]:
    """
    Find all chat files in the specified directories.
    
    Args:
        directories: List of directories to search for chat files
        
    Returns:
        List of paths to found chat files
    """
    if directories is None:
        directories = ['.', 'chat_exports', 'markdown_chats']
    
    all_files = []
    
    # Collect files from all specified directories
    for directory in directories:
        if os.path.exists(directory):
            for f in os.listdir(directory):
                if f.endswith('.md') and f.startswith('chat_'):
                    all_files.append(os.path.join(directory, f))
    
    return all_files


def group_chat_files(files: List[str]) -> Dict[str, List[str]]:
    """
    Group chat files by their workspace hash.
    
    Args:
        files: List of chat file paths
        
    Returns:
        Dictionary mapping workspace hashes to lists of file paths
    """
    chat_groups = {}
    
    for file in files:
        match = re.match(r'.*chat_([a-f0-9]+)(?:_([a-f0-9-]+))?.md', file)
        if match:
            hash_val = match.group(1)
            if hash_val not in chat_groups:
                chat_groups[hash_val] = []
            chat_groups[hash_val].append(file)
    
    return chat_groups


def list_chat_files(directories: List[str] = None) -> Dict[str, List[str]]:
    """
    List all chat files in the specified directories, grouped by workspace hash.
    
    Args:
        directories: List of directories to search for chat files
        
    Returns:
        Dictionary mapping workspace hashes to lists of file paths
    """
    all_files = find_chat_files(directories)
    
    if not all_files:
        logger.info("No chat files found in the specified directories.")
        return {}
    
    # Group files by hash
    chat_groups = group_chat_files(all_files)
    
    # Print chat groups
    for i, (hash_val, group_files) in enumerate(chat_groups.items()):
        logger.info("%d. Group %s... (%d files)", i + 1, hash_val[:8], len(group_files))
        
        # Identify parent files
        parent_files = [f for f in group_files if re.match(r'.*chat_[a-f0-9]+\.md$', f)]
        other_files = [f for f in group_files if f not in parent_files]
        
        # Print parent files first
        for parent_file in parent_files:
            logger.info("   - %s (Parent)", parent_file)
        
        # Then print child files
        for j, file in enumerate(sorted(other_files)):
            logger.info("   %d. %s", j + 1, file)
        logger.info("")
    
    return chat_groups


def view_chat_file(filepath: str) -> Optional[str]:
    """
    Read and return the contents of a chat file.
    
    Args:
        filepath: Path to the chat file
        
    Returns:
        The file contents as a string, or None if the file couldn't be read
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return content
    except Exception as e:
        logger.error("Error reading file %s: %s", filepath, e)
        return None


def display_chat_file(filepath: str) -> bool:
    """
    Display the contents of a chat file to the console.
    
    Args:
        filepath: Path to the chat file
        
    Returns:
        True if the file was successfully displayed, False otherwise
    """
    content = view_chat_file(filepath)
    if content:
        logger.info("\n%s\n%s\n%s\n", '=' * 80, filepath, '=' * 80)
        logger.info(content)
        return True
    return False


def find_chat_file(filename: str, directories: List[str] = None) -> Optional[str]:
    """
    Find a chat file by name or partial name in the specified directories.
    
    Args:
        filename: Name or partial name of the chat file to find
        directories: List of directories to search
        
    Returns:
        Full path to the found file, or None if no matching file was found
    """
    if directories is None:
        directories = ['.', 'chat_exports', 'markdown_chats']
    
    # First, check if it's a direct file path
    if os.path.isfile(filename):
        return filename
    
    # Try to find the file in common directories
    for directory in directories:
        potential_path = os.path.join(directory, filename)
        if os.path.isfile(potential_path):
            return potential_path
    
    # Try to find files that contain the filename
    all_files = find_chat_files(directories)
    for file in all_files:
        if filename in file:
            return file
    
    return None 
