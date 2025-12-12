"""
Legacy chat importer.

Imports old-format chat_data_*.json files (with tabs/bubbles structure)
into the normalized database.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.core.db import ChatDatabase
from src.core.models import Chat, Message, Workspace, ChatMode, MessageRole

logger = logging.getLogger(__name__)


class LegacyChatImporter:
    """
    Imports legacy chat exports into normalized database.
    
    Handles old format with tabs/bubbles structure.
    """
    
    def __init__(self, db: ChatDatabase):
        """
        Initialize importer.
        
        Parameters
        ----
        db : ChatDatabase
            Database instance
        """
        self.db = db
    
    def import_file(self, file_path: Path, workspace_hash: Optional[str] = None) -> int:
        """
        Import a legacy chat JSON file.
        
        Parameters
        ----
        file_path : Path
            Path to chat_data_*.json file
        workspace_hash : str, optional
            Workspace hash extracted from filename
            
        Returns
        ----
        int
            Number of chats imported
        """
        if not file_path.exists():
            logger.error("File not found: %s", file_path)
            return 0
        
        # Extract workspace hash from filename if not provided
        if not workspace_hash:
            filename = file_path.stem
            if filename.startswith("chat_data_"):
                workspace_hash = filename[len("chat_data_"):]
        
        # Read JSON file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Failed to read/parse %s: %s", file_path, e)
            return 0
        
        # Find workspace or create placeholder
        workspace_id = None
        if workspace_hash:
            workspace = Workspace(
                workspace_hash=workspace_hash,
                folder_uri="",
                resolved_path=None,
            )
            workspace_id = self.db.upsert_workspace(workspace)
        
        # Parse old format
        imported_count = 0
        
        for item in data:
            item_data = item.get('data')
            if not isinstance(item_data, dict):
                continue
            
            # Look for tabs structure
            tabs = item_data.get('tabs', [])
            if not tabs:
                continue
            
            # Process each tab as a separate chat
            for tab in tabs:
                tab_id = tab.get('tabId', '')
                chat_title = tab.get('chatTitle', 'Untitled Chat')
                bubbles = tab.get('bubbles', [])
                
                if not bubbles:
                    continue
                
                # Convert bubbles to messages
                messages = []
                for bubble in bubbles:
                    bubble_type = bubble.get('type', '').lower()
                    
                    if bubble_type == 'user':
                        role = MessageRole.USER
                    elif bubble_type in ('ai', 'assistant'):
                        role = MessageRole.ASSISTANT
                    else:
                        continue  # Skip unknown types
                    
                    text = bubble.get('text') or bubble.get('rawText') or ''
                    
                    # Extract timestamp
                    created_at = None
                    if bubble.get('timestamp'):
                        try:
                            created_at = datetime.fromtimestamp(bubble['timestamp'] / 1000)
                        except (ValueError, TypeError):
                            pass
                    
                    message = Message(
                        role=role,
                        text=text,
                        rich_text="",
                        created_at=created_at,
                        cursor_bubble_id=bubble.get('id'),
                        raw_json=bubble,
                    )
                    messages.append(message)
                
                if not messages:
                    continue
                
                # Create chat
                chat = Chat(
                    cursor_composer_id=tab_id or f"legacy_{imported_count}",
                    workspace_id=workspace_id,
                    title=chat_title,
                    mode=ChatMode.CHAT,
                    created_at=messages[0].created_at if messages else datetime.now(),
                    last_updated_at=messages[-1].created_at if messages else datetime.now(),
                    source="legacy",
                    messages=messages,
                    relevant_files=[],
                )
                
                # Store in database
                try:
                    self.db.upsert_chat(chat)
                    imported_count += 1
                except Exception as e:
                    logger.error("Failed to import chat %s: %s", tab_id, e)
        
        logger.info("Imported %d chats from %s", imported_count, file_path)
        return imported_count
    
    def import_directory(self, directory: Path, pattern: str = "chat_data_*.json") -> Dict[str, int]:
        """
        Import all legacy files from a directory.
        
        Parameters
        ----
        directory : Path
            Directory containing legacy JSON files
        pattern : str
            Filename pattern to match
            
        Returns
        ----
        Dict[str, int]
            Statistics: {"files": count, "chats": count, "errors": count}
        """
        if not directory.exists():
            logger.error("Directory not found: %s", directory)
            return {"files": 0, "chats": 0, "errors": 0}
        
        stats = {"files": 0, "chats": 0, "errors": 0}
        
        for file_path in directory.glob(pattern):
            try:
                count = self.import_file(file_path)
                stats["files"] += 1
                stats["chats"] += count
            except Exception as e:
                logger.error("Error importing %s: %s", file_path, e)
                stats["errors"] += 1
        
        logger.info("Legacy import complete: %d files, %d chats, %d errors",
                   stats["files"], stats["chats"], stats["errors"])
        
        return stats

