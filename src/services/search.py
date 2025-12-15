"""
Search service for querying aggregated chats.
"""
import logging
from typing import List, Dict, Optional, Any

from src.core.db import ChatDatabase

logger = logging.getLogger(__name__)


class ChatSearchService:
    """
    Provides search functionality over aggregated chats.
    """
    
    def __init__(self, db: ChatDatabase):
        """
        Initialize search service.
        
        Parameters
        ----
        db : ChatDatabase
            Database instance
        """
        self.db = db
    
    def search(self, query: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search chats by text content.
        
        Parameters
        ----
        query : str
            Search query (supports FTS5 syntax)
        limit : int
            Maximum number of results
        offset : int
            Offset for pagination
            
        Returns
        ----
        List[Dict[str, Any]]
            List of matching chats
        """
        return self.db.search_chats(query, limit, offset)
    
    def list_chats(self, workspace_id: Optional[int] = None, 
                   limit: int = 100, offset: int = 0,
                   empty_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List chats with optional workspace and empty status filters.
        
        Parameters
        ----
        workspace_id : int, optional
            Filter by workspace ID
        limit : int
            Maximum number of results
        offset : int
            Offset for pagination
        empty_filter : str, optional
            Filter by empty status: 'empty' (messages_count = 0), 'non_empty' (messages_count > 0), or None (all)
            
        Returns
        ----
        List[Dict[str, Any]]
            List of chats
        """
        return self.db.list_chats(workspace_id, limit, offset, empty_filter)
    
    def get_chat(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific chat with all messages.
        
        Parameters
        ----
        chat_id : int
            Chat ID
            
        Returns
        ----
        Dict[str, Any]
            Chat data, or None if not found
        """
        return self.db.get_chat(chat_id)
    
    def count_chats(self, workspace_id: Optional[int] = None, empty_filter: Optional[str] = None) -> int:
        """
        Count total chats, optionally filtered by workspace and empty status.
        
        Parameters
        ----
        workspace_id : int, optional
            Filter by workspace
        empty_filter : str, optional
            Filter by empty status: 'empty' (messages_count = 0), 'non_empty' (messages_count > 0), or None (all)
            
        Returns
        ----
        int
            Total count
        """
        return self.db.count_chats(workspace_id, empty_filter)
    
    def count_search(self, query: str) -> int:
        """
        Count search results for a query.
        
        Parameters
        ----
        query : str
            Search query
            
        Returns
        ----
        int
            Total count of matching chats
        """
        return self.db.count_search(query)

