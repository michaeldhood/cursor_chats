"""
Module for extracting chat data from Cursor's SQLite database.
"""
import os
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

from src.core.config import get_cursor_workspace_storage_path

logger = logging.getLogger(__name__)


def get_cursor_chat_path() -> str:
    """
    Get the path to Cursor chat data based on the operating system.
    
    Returns:
        str: Path to Cursor workspace storage directory
        
    Raises:
        OSError: If running on an unsupported operating system
    """
    return str(get_cursor_workspace_storage_path())


def read_sqlite_db(db_path: str) -> Optional[List[Dict[str, Any]]]:
    """
    Read and extract chat data from the SQLite database.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        List of dictionaries containing chat data or None if extraction failed
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First, check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        logger.debug("Tables in database: %s", [table[0] for table in tables])
        
        # Try to find chat-related data in the ItemTable
        cursor.execute("SELECT key, value FROM ItemTable WHERE key LIKE '%chat%' OR key LIKE '%conversation%';")
        rows = cursor.fetchall()
        
        chat_data = []
        for key, value in rows:
            try:
                # Try to parse the value as JSON
                parsed_value = json.loads(value)
                chat_data.append({
                    'key': key,
                    'data': parsed_value
                })
                logger.debug("Found chat data with key: %s", key)
            except json.JSONDecodeError:
                logger.debug("Non-JSON data found for key: %s", key)
        
        return chat_data

    except sqlite3.Error as e:
        logger.error("SQLite error: %s", str(e))
        return None

    finally:
        if conn:
            conn.close()


def get_project_name(workspace_path: str) -> str:
    """
    Get the project name from the workspace.json file.
    
    Args:
        workspace_path: Path to workspace.json file
        
    Returns:
        Project name or empty string if not found
    """
    try:
        with open(workspace_path, 'r', encoding='utf-8') as f:
            workspace_data = json.load(f)
            return workspace_data.get('folder', '')
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error("Error reading workspace.json: %s", str(e))
        return ""


def analyze_workspace(workspace_path: str, output_dir: str = '.', filename_pattern: str = 'chat_data_{workspace}.json') -> Optional[str]:
    """
    Analyze the contents of a workspace folder and extract chat data.
    
    Args:
        workspace_path: Path to the workspace folder
        output_dir: Directory to save extracted files
        filename_pattern: Pattern for output filenames
        
    Returns:
        Path to the saved file if data was extracted, None otherwise
    """
    logger.info("\nAnalyzing workspace: %s", os.path.basename(workspace_path))
    
    # Look specifically for state.vscdb files
    for root, dirs, files in os.walk(workspace_path):
        if 'workspace.json' in files:
            workspace_json_path = os.path.join(root, 'workspace.json')
            logger.info("Found workspace.json at: %s", os.path.relpath(workspace_json_path, workspace_path))
            project_name = get_project_name(workspace_json_path)
            logger.info("Project name: %s", project_name)
        
        if 'state.vscdb' in files:
            db_path = os.path.join(root, 'state.vscdb')
            logger.info("Found state.vscdb at: %s", os.path.relpath(db_path, workspace_path))
            
            # Read and analyze the database
            chat_data = read_sqlite_db(db_path)
            
            if chat_data:
                # Save extracted chat data to a JSON file
                workspace_id = os.path.basename(workspace_path)
                filename = filename_pattern.format(workspace=workspace_id)
                output_file = os.path.join(output_dir, filename)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(chat_data, f, indent=2)
                logger.info("Saved chat data to %s", output_file)
                return output_file
    
    return None


def extract_chats(output_dir: str = '.', filename_pattern: str = 'chat_data_{workspace}.json') -> List[str]:
    """
    Extract and analyze chat data from Cursor workspaces.
    
    Args:
        output_dir: Directory to save extracted files
        filename_pattern: Pattern for output filenames
    
    Returns:
        List of paths to extracted JSON files
    """
    base_path = str(get_cursor_workspace_storage_path())
    extracted_files = []
    
    if not os.path.exists(base_path):
        logger.error("Workspace directory not found at: %s", base_path)
        return extracted_files

    logger.info("Found Cursor workspace directory at: %s", base_path)
    
    # Analyze each workspace folder
    workspaces = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    
    if not workspaces:
        logger.info("No workspace folders found")
        return extracted_files

    logger.info("Found %d workspace folders", len(workspaces))
    
    for workspace in workspaces:
        workspace_path = os.path.join(base_path, workspace)
        output_file = analyze_workspace(workspace_path, output_dir, filename_pattern)
        if output_file:
            extracted_files.append(output_file)
    
    return extracted_files 
