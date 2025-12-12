"""
Chat aggregator service.

Orchestrates extraction from Cursor databases, linking workspace metadata
to global composer conversations, and storing normalized data.
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.core.db import ChatDatabase
from src.core.models import Chat, Message, Workspace, ChatMode, MessageRole
from src.readers.workspace_reader import WorkspaceStateReader
from src.readers.global_reader import GlobalComposerReader

logger = logging.getLogger(__name__)


class ChatAggregator:
    """
    Aggregates chats from Cursor databases into normalized local database.
    
    Handles:
    - Reading workspace metadata
    - Reading global composer conversations
    - Linking composers to workspaces
    - Converting to domain models
    - Storing in local database
    """
    
    def __init__(self, db: ChatDatabase):
        """
        Initialize aggregator.
        
        Parameters
        ----
        db : ChatDatabase
            Database instance for storing aggregated data
        """
        self.db = db
        self.workspace_reader = WorkspaceStateReader()
        self.global_reader = GlobalComposerReader()
    
    def _convert_composer_to_chat(self, composer_data: Dict[str, Any], 
                                   workspace_id: Optional[int] = None) -> Optional[Chat]:
        """
        Convert Cursor composer data to Chat domain model.
        
        Parameters
        ----
        composer_data : Dict[str, Any]
            Raw composer data from global database
        workspace_id : int, optional
            Workspace ID if known
            
        Returns
        ----
        Chat
            Chat domain model, or None if conversion fails
        """
        composer_id = composer_data.get("composerId")
        if not composer_id:
            return None
        
        # Determine mode
        force_mode = composer_data.get("forceMode", "chat")
        unified_mode = composer_data.get("unifiedMode", "chat")
        mode_map = {
            "chat": ChatMode.CHAT,
            "edit": ChatMode.EDIT,
            "agent": ChatMode.AGENT,
            "composer": ChatMode.COMPOSER,
        }
        mode = mode_map.get(force_mode or unified_mode, ChatMode.CHAT)
        
        # Extract title
        title = composer_data.get("name") or composer_data.get("subtitle") or "Untitled Chat"
        
        # Extract timestamps
        created_at = None
        if composer_data.get("createdAt"):
            try:
                created_at = datetime.fromtimestamp(composer_data["createdAt"] / 1000)
            except (ValueError, TypeError):
                pass
        
        last_updated_at = None
        if composer_data.get("lastUpdatedAt"):
            try:
                last_updated_at = datetime.fromtimestamp(composer_data["lastUpdatedAt"] / 1000)
            except (ValueError, TypeError):
                pass
        
        # Extract conversation
        conversation = composer_data.get("conversation", [])
        messages = []
        relevant_files = set()
        
        for bubble in conversation:
            bubble_type = bubble.get("type")
            if bubble_type == 1:  # User message
                role = MessageRole.USER
            elif bubble_type == 2:  # AI response
                role = MessageRole.ASSISTANT
            else:
                continue  # Skip unknown types
            
            text = bubble.get("text", "")
            rich_text = bubble.get("richText", "")
            
            # Extract timestamp
            msg_created_at = None
            if bubble.get("createdAt"):
                try:
                    msg_created_at = datetime.fromtimestamp(bubble["createdAt"] / 1000)
                except (ValueError, TypeError):
                    pass
            
            message = Message(
                role=role,
                text=text,
                rich_text=rich_text,
                created_at=msg_created_at or created_at,  # Fallback to chat created_at
                cursor_bubble_id=bubble.get("bubbleId"),
                raw_json=bubble,
            )
            messages.append(message)
            
            # Extract relevant files
            for file_path in bubble.get("relevantFiles", []):
                relevant_files.add(file_path)
        
        # Create chat
        chat = Chat(
            cursor_composer_id=composer_id,
            workspace_id=workspace_id,
            title=title,
            mode=mode,
            created_at=created_at,
            last_updated_at=last_updated_at,
            source="cursor",
            messages=messages,
            relevant_files=list(relevant_files),
        )
        
        return chat
    
    def _build_workspace_map(self) -> Dict[str, int]:
        """
        Build mapping from workspace_hash to workspace_id.
        
        Returns
        ----
        Dict[str, int]
            Mapping of workspace_hash -> workspace_id
        """
        workspace_map = {}
        workspaces_metadata = self.workspace_reader.read_all_workspaces()
        
        for workspace_hash, metadata in workspaces_metadata.items():
            workspace = Workspace(
                workspace_hash=workspace_hash,
                folder_uri=metadata.get("project_path", ""),
                resolved_path=metadata.get("project_path", ""),
            )
            workspace_id = self.db.upsert_workspace(workspace)
            workspace_map[workspace_hash] = workspace_id
        
        return workspace_map
    
    def _build_composer_to_workspace_map(self) -> Dict[str, Optional[int]]:
        """
        Build mapping from composer_id to workspace_id.
        
        Returns
        ----
        Dict[str, Optional[int]]
            Mapping of composer_id -> workspace_id (None if unknown)
        """
        composer_to_workspace = {}
        workspaces_metadata = self.workspace_reader.read_all_workspaces()
        workspace_map = self._build_workspace_map()
        
        for workspace_hash, metadata in workspaces_metadata.items():
            workspace_id = workspace_map.get(workspace_hash)
            
            # Extract composer IDs from workspace metadata
            composer_ids = self.workspace_reader.get_composer_ids_for_workspace(workspace_hash)
            for composer_id in composer_ids:
                composer_to_workspace[composer_id] = workspace_id
        
        return composer_to_workspace
    
    def ingest_all(self, progress_callback: Optional[callable] = None) -> Dict[str, int]:
        """
        Ingest all chats from Cursor databases.
        
        Parameters
        ----
        progress_callback : callable, optional
            Callback function(composer_id, total, current) for progress updates
            
        Returns
        ----
        Dict[str, int]
            Statistics: {"ingested": count, "skipped": count, "errors": count}
        """
        logger.info("Starting chat ingestion from Cursor databases...")
        
        # Build workspace and composer mappings
        logger.info("Building workspace mappings...")
        composer_to_workspace = self._build_composer_to_workspace_map()
        
        # Read all composers from global database
        logger.info("Reading composers from global database...")
        stats = {"ingested": 0, "skipped": 0, "errors": 0}
        
        composers = list(self.global_reader.read_all_composers())
        total = len(composers)
        
        logger.info("Found %d composers to process", total)
        
        for idx, composer_info in enumerate(composers):
            composer_id = composer_info["composer_id"]
            composer_data = composer_info["data"]
            
            if progress_callback:
                progress_callback(composer_id, total, idx + 1)
            
            try:
                # Find workspace for this composer
                workspace_id = composer_to_workspace.get(composer_id)
                
                # Convert to domain model
                chat = self._convert_composer_to_chat(composer_data, workspace_id)
                if not chat:
                    stats["skipped"] += 1
                    continue
                
                # Store in database
                self.db.upsert_chat(chat)
                stats["ingested"] += 1
                
                if (idx + 1) % 100 == 0:
                    logger.info("Processed %d/%d composers...", idx + 1, total)
                    
            except Exception as e:
                logger.error("Error processing composer %s: %s", composer_id, e)
                stats["errors"] += 1
        
        logger.info("Ingestion complete: %d ingested, %d skipped, %d errors", 
                   stats["ingested"], stats["skipped"], stats["errors"])
        
        return stats

