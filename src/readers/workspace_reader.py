"""
Reader for workspace-level Cursor state databases.

Extracts metadata from workspaceStorage/{hash}/state.vscdb including:
- aiService.prompts and aiService.generations
- composer.composerData
- workspace.json for project path mapping
"""
import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def get_cursor_workspace_storage_path() -> Path:
    """
    Get the path to Cursor workspace storage directory.
    
    Returns
    ----
    Path
        Path to workspaceStorage directory
        
    Raises
    ---
    OSError
        If running on unsupported OS
    """
    import platform
    system = platform.system()
    home = Path.home()
    
    if system == 'Darwin':  # macOS
        return home / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage"
    elif system == 'Windows':
        return Path(home) / "AppData" / "Roaming" / "Cursor" / "User" / "workspaceStorage"
    elif system == 'Linux':
        # Check for WSL
        if os.path.exists('/proc/version'):
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    # WSL - get Windows path
                    windows_home = os.popen('cd /mnt/c && cmd.exe /c echo %USERPROFILE%').read().strip()
                    windows_path = Path(windows_home) / "AppData" / "Roaming" / "Cursor" / "User" / "workspaceStorage"
                    wsl_path = os.popen(f'wslpath "{windows_path}"').read().strip()
                    return Path(wsl_path)
        # Native Linux
        return home / ".config" / "Cursor" / "User" / "workspaceStorage"
    else:
        raise OSError(f"Unsupported operating system: {system}")


class WorkspaceStateReader:
    """
    Reads metadata from workspace state databases.
    
    Extracts composer IDs, prompts, generations, and workspace information
    to help link global composer data to specific workspaces.
    """
    
    def __init__(self, workspace_storage_path: Optional[Path] = None):
        """
        Initialize reader.
        
        Parameters
        ----
        workspace_storage_path : Path, optional
            Path to workspaceStorage directory. If None, uses default OS location.
        """
        if workspace_storage_path is None:
            workspace_storage_path = get_cursor_workspace_storage_path()
        self.workspace_storage_path = workspace_storage_path
    
    def read_workspace_metadata(self, workspace_hash: str) -> Optional[Dict[str, Any]]:
        """
        Read metadata from a specific workspace.
        
        Parameters
        ----
        workspace_hash : str
            Workspace hash (folder name)
            
        Returns
        ----
        Dict[str, Any]
            Workspace metadata including prompts, generations, composer data, and project path
        """
        workspace_path = self.workspace_storage_path / workspace_hash
        if not workspace_path.exists():
            return None
        
        db_path = workspace_path / "state.vscdb"
        if not db_path.exists():
            return None
        
        metadata = {
            "workspace_hash": workspace_hash,
            "prompts": [],
            "generations": [],
            "composer_data": None,
            "project_path": None,
        }
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Read aiService.prompts
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'aiService.prompts'")
            row = cursor.fetchone()
            if row:
                try:
                    metadata["prompts"] = json.loads(row[0])
                except json.JSONDecodeError:
                    logger.warning("Failed to parse aiService.prompts for workspace %s", workspace_hash)
            
            # Read aiService.generations
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'aiService.generations'")
            row = cursor.fetchone()
            if row:
                try:
                    metadata["generations"] = json.loads(row[0])
                except json.JSONDecodeError:
                    logger.warning("Failed to parse aiService.generations for workspace %s", workspace_hash)
            
            # Read composer.composerData
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'composer.composerData'")
            row = cursor.fetchone()
            if row:
                try:
                    metadata["composer_data"] = json.loads(row[0])
                except json.JSONDecodeError:
                    logger.warning("Failed to parse composer.composerData for workspace %s", workspace_hash)
            
            conn.close()
            
            # Read workspace.json for project path
            workspace_json_path = workspace_path / "workspace.json"
            if workspace_json_path.exists():
                try:
                    with open(workspace_json_path, 'r', encoding='utf-8') as f:
                        workspace_data = json.load(f)
                        metadata["project_path"] = workspace_data.get("folder", "")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning("Failed to read workspace.json for %s: %s", workspace_hash, e)
            
        except sqlite3.Error as e:
            logger.error("Error reading workspace %s: %s", workspace_hash, e)
            return None
        
        return metadata
    
    def read_all_workspaces(self) -> Dict[str, Dict[str, Any]]:
        """
        Read metadata from all workspaces.
        
        Returns
        ----
        Dict[str, Dict[str, Any]]
            Dictionary mapping workspace_hash to metadata
        """
        if not self.workspace_storage_path.exists():
            logger.warning("Workspace storage path does not exist: %s", self.workspace_storage_path)
            return {}
        
        workspaces = {}
        for workspace_dir in self.workspace_storage_path.iterdir():
            if workspace_dir.is_dir():
                workspace_hash = workspace_dir.name
                metadata = self.read_workspace_metadata(workspace_hash)
                if metadata:
                    workspaces[workspace_hash] = metadata
        
        logger.info("Read metadata from %d workspaces", len(workspaces))
        return workspaces
    
    def get_composer_ids_for_workspace(self, workspace_hash: str) -> List[str]:
        """
        Extract all composer IDs referenced in a workspace.
        
        Parameters
        ----
        workspace_hash : str
            Workspace hash
            
        Returns
        ----
        List[str]
            List of composer UUIDs
        """
        metadata = self.read_workspace_metadata(workspace_hash)
        if not metadata:
            return []
        
        composer_ids = []
        
        # From composer_data
        if metadata.get("composer_data") and isinstance(metadata["composer_data"], dict):
            all_composers = metadata["composer_data"].get("allComposers", [])
            for composer in all_composers:
                composer_id = composer.get("composerId")
                if composer_id:
                    composer_ids.append(composer_id)
        
        # From generations (they reference composer IDs)
        for gen in metadata.get("generations", []):
            composer_id = gen.get("generationUUID")  # Note: might be different field
            if composer_id:
                composer_ids.append(composer_id)
        
        return list(set(composer_ids))  # Deduplicate

