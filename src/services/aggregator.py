"""
Chat aggregator service.

Orchestrates extraction from Cursor databases, linking workspace metadata
to global composer conversations, and storing normalized data.
"""
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

from src.core.db import ChatDatabase
from src.core.models import Chat, Message, Workspace, ChatMode, MessageRole, MessageType
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
    
    def _resolve_conversation_from_headers(
        self, composer_id: str, headers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Resolve conversation bubbles from headers-only format.
        
        In newer Cursor versions, conversation data is split:
        - fullConversationHeadersOnly: list of {bubbleId, type} headers
        - Actual content stored separately as bubbleId:{composerId}:{bubbleId} keys
        
        Uses batch query for efficiency when multiple bubbles need to be fetched.
        
        Parameters
        ----
        composer_id : str
            Composer UUID
        headers : List[Dict[str, Any]]
            List of bubble headers with bubbleId and type
            
        Returns
        ----
        List[Dict[str, Any]]
            List of full bubble objects with text/richText content
        """
        # Extract all bubble IDs
        bubble_ids = [header.get("bubbleId") for header in headers if header.get("bubbleId")]
        
        # Batch fetch all bubbles in one query
        bubbles_map = self.global_reader.read_bubbles_batch(composer_id, bubble_ids)
        
        # Build conversation list, preserving header order
        conversation = []
        for header in headers:
            bubble_id = header.get("bubbleId")
            if not bubble_id:
                continue
            
            bubble_data = bubbles_map.get(bubble_id)
            if bubble_data:
                # Merge header info (type) with full bubble data
                bubble = {**bubble_data}
                # Ensure type is present (from header if not in bubble)
                if "type" not in bubble:
                    bubble["type"] = header.get("type")
                conversation.append(bubble)
            else:
                # Fallback: use header only (will have no text)
                conversation.append(header)
        
        return conversation
    
    def _classify_bubble(self, bubble: Dict[str, Any]) -> MessageType:
        """
        Classify a bubble by its content type.
        
        Parameters
        ----
        bubble : Dict[str, Any]
            Raw bubble data from Cursor
            
        Returns
        ----
        MessageType
            Classification of the bubble content
        """
        text = bubble.get("text", "")
        rich_text = bubble.get("richText", "")
        
        # Has content -> response
        if text or rich_text:
            return MessageType.RESPONSE
        
        # Check for tool-related fields
        # Cursor stores tool calls with various metadata fields
        if (bubble.get("codeBlock") or 
            bubble.get("toolFormerResult") or
            bubble.get("toolCalls") or
            bubble.get("toolCall")):
            return MessageType.TOOL_CALL
        
        # Check for thinking/reasoning metadata
        # This is less common but may exist in some formats
        if bubble.get("thinking") or bubble.get("reasoning"):
            return MessageType.THINKING
        
        # Default empty
        return MessageType.EMPTY
    
    def _convert_composer_to_chat(self, composer_data: Dict[str, Any], 
                                   workspace_id: Optional[int] = None,
                                   composer_head: Optional[Dict[str, Any]] = None) -> Optional[Chat]:
        """
        Convert Cursor composer data to Chat domain model.
        
        Parameters
        ----
        composer_data : Dict[str, Any]
            Raw composer data from global database
        workspace_id : int, optional
            Workspace ID if known
        composer_head : Dict[str, Any], optional
            Composer head metadata from workspace (for title enrichment)
            
        Returns
        ----
        Chat
            Chat domain model, or None if conversion fails
        """
        composer_id = composer_data.get("composerId")
        if not composer_id:
            return None
        
        # Determine mode (prefer workspace head, then global data)
        force_mode = None
        unified_mode = None
        
        if composer_head:
            force_mode = composer_head.get("forceMode")
            unified_mode = composer_head.get("unifiedMode")
        
        if not force_mode:
            force_mode = composer_data.get("forceMode", "chat")
        if not unified_mode:
            unified_mode = composer_data.get("unifiedMode", "chat")
        
        mode_map = {
            "chat": ChatMode.CHAT,
            "edit": ChatMode.EDIT,
            "agent": ChatMode.AGENT,
            "composer": ChatMode.COMPOSER,
        }
        mode = mode_map.get(force_mode or unified_mode, ChatMode.CHAT)
        
        # Extract title with enrichment priority:
        # 1. workspace composer head name
        # 2. workspace composer head subtitle
        # 3. global composer data name/subtitle
        # 4. fallback
        title = None
        if composer_head:
            title = composer_head.get("name") or composer_head.get("subtitle")
        
        if not title:
            title = composer_data.get("name") or composer_data.get("subtitle")
        
        if not title:
            title = "Untitled Chat"
        
        # Extract timestamps (prefer workspace head, then global data)
        created_at = None
        if composer_head and composer_head.get("createdAt"):
            try:
                created_at = datetime.fromtimestamp(composer_head["createdAt"] / 1000)
            except (ValueError, TypeError):
                pass
        
        if not created_at and composer_data.get("createdAt"):
            try:
                created_at = datetime.fromtimestamp(composer_data["createdAt"] / 1000)
            except (ValueError, TypeError):
                pass
        
        last_updated_at = None
        if composer_head and composer_head.get("lastUpdatedAt"):
            try:
                last_updated_at = datetime.fromtimestamp(composer_head["lastUpdatedAt"] / 1000)
            except (ValueError, TypeError):
                pass
        
        if not last_updated_at and composer_data.get("lastUpdatedAt"):
            try:
                last_updated_at = datetime.fromtimestamp(composer_data["lastUpdatedAt"] / 1000)
            except (ValueError, TypeError):
                pass
        
        # Extract conversation - try multiple formats
        # Format 1: Old style with full conversation array
        conversation = composer_data.get("conversation", [])
        
        # Format 2: New style with headers-only + separate bubble storage
        # If conversation is empty, try fullConversationHeadersOnly
        if not conversation:
            headers = composer_data.get("fullConversationHeadersOnly", [])
            if headers:
                conversation = self._resolve_conversation_from_headers(
                    composer_id, headers
                )
        
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
            
            # Classify the bubble type
            message_type = self._classify_bubble(bubble)
            
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
                message_type=message_type,
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
    
    def _load_workspace_data(self) -> Tuple[Dict[str, int], Dict[str, Optional[int]], Dict[str, Dict[str, Any]]]:
        """
        Load workspace data once and build all three mappings in a single pass.
        
        This method reads workspaces only once, avoiding redundant database opens.
        
        Returns
        ----
        tuple[Dict[str, int], Dict[str, Optional[int]], Dict[str, Dict[str, Any]]]
            Tuple of (workspace_map, composer_to_workspace, composer_heads)
            - workspace_map: workspace_hash -> workspace_id
            - composer_to_workspace: composer_id -> workspace_id (None if unknown)
            - composer_heads: composer_id -> composer head metadata
        """
        # Read all workspaces once
        workspaces_metadata = self.workspace_reader.read_all_workspaces()
        
        workspace_map = {}
        composer_to_workspace = {}
        composer_heads = {}
        
        # Build all three mappings in one pass
        for workspace_hash, metadata in workspaces_metadata.items():
            # Build workspace map
            workspace = Workspace(
                workspace_hash=workspace_hash,
                folder_uri=metadata.get("project_path", ""),
                resolved_path=metadata.get("project_path", ""),
            )
            workspace_id = self.db.upsert_workspace(workspace)
            workspace_map[workspace_hash] = workspace_id
            
            # Extract composer data from metadata (already loaded, no need to re-read)
            composer_data = metadata.get("composer_data")
            if composer_data and isinstance(composer_data, dict):
                all_composers = composer_data.get("allComposers", [])
                
                for composer in all_composers:
                    composer_id = composer.get("composerId")
                    if composer_id:
                        # Build composer_to_workspace map
                        composer_to_workspace[composer_id] = workspace_id
                        
                        # Build composer_heads map
                        composer_heads[composer_id] = {
                            "name": composer.get("name"),
                            "subtitle": composer.get("subtitle"),
                            "createdAt": composer.get("createdAt"),
                            "lastUpdatedAt": composer.get("lastUpdatedAt"),
                            "unifiedMode": composer.get("unifiedMode"),
                            "forceMode": composer.get("forceMode"),
                        }
        
        return workspace_map, composer_to_workspace, composer_heads
    
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
        
        # Load workspace data once and build all mappings
        logger.info("Loading workspace data...")
        workspace_map, composer_to_workspace, composer_heads = self._load_workspace_data()
        logger.info("Loaded %d workspaces, %d composer mappings", 
                   len(workspace_map), len(composer_to_workspace))
        
        # Stream composers from global database (don't materialize)
        logger.info("Streaming composers from global database...")
        stats = {"ingested": 0, "skipped": 0, "errors": 0}
        
        # Get approximate total for progress (optional, can skip if slow)
        try:
            import sqlite3
            conn = sqlite3.connect(str(self.global_reader.db_path))
            cursor = conn.cursor()
            # Use range query with index for fast count
            cursor.execute("SELECT COUNT(*) FROM cursorDiskKV WHERE key >= ? AND key < ?", 
                         ("composerData:", "composerData;"))
            total = cursor.fetchone()[0]
            conn.close()
            logger.info("Found approximately %d composers to process", total)
        except Exception as e:
            logger.warning("Could not get total count: %s", e)
            total = None
        
        # Stream processing
        idx = 0
        for composer_info in self.global_reader.read_all_composers():
            idx += 1
            composer_id = composer_info["composer_id"]
            composer_data = composer_info["data"]
            
            if progress_callback and total:
                progress_callback(composer_id, total, idx)
            
            try:
                # Find workspace for this composer
                workspace_id = composer_to_workspace.get(composer_id)
                
                # Get composer head for title enrichment
                composer_head = composer_heads.get(composer_id)
                
                # Convert to domain model
                chat = self._convert_composer_to_chat(composer_data, workspace_id, composer_head)
                if not chat:
                    stats["skipped"] += 1
                    continue
                
                # Store in database
                self.db.upsert_chat(chat)
                stats["ingested"] += 1
                
                if idx % 100 == 0:
                    logger.info("Processed %d composers...", idx)
                    
            except Exception as e:
                logger.error("Error processing composer %s: %s", composer_id, e)
                stats["errors"] += 1
        
        logger.info("Ingestion complete: %d ingested, %d skipped, %d errors", 
                   stats["ingested"], stats["skipped"], stats["errors"])
        
        return stats

