"""
Search service for querying aggregated chats.

Provides Obsidian-like instant search with:
- Full-text search across titles, messages, tags, and files
- Prefix matching for search-as-you-type
- Highlighted snippets showing match context
- BM25 relevance ranking
"""
import logging
from typing import List, Dict, Optional, Any, Tuple

from src.core.db import ChatDatabase

logger = logging.getLogger(__name__)


class ChatSearchService:
    """
    Provides search functionality over aggregated chats.
    
    Features:
    - instant_search(): Fast typeahead with prefix matching
    - search(): Full paginated search with snippets
    - Automatic relevance ranking via BM25
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
    
    def instant_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fast instant search for live typeahead.
        
        Optimized for speed - returns quickly with highlighted snippets.
        Searches across chat titles, message content, tags, and file paths.
        
        Parameters
        ----
        query : str
            Search query (prefix matching applied automatically)
        limit : int
            Maximum results (default 10 for fast UI)
            
        Returns
        ----
        List[Dict[str, Any]]
            Results with 'snippet' field containing highlighted matches
        """
        return self.db.instant_search(query, limit)
    
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
        # Use the new unified search with snippets
        results, _ = self.db.search_with_snippets(query, limit, offset)
        return results
    
    def search_with_total(self, query: str, limit: int = 50, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search with total count for pagination.
        
        Parameters
        ----
        query : str
            Search query
        limit : int
            Results per page
        offset : int
            Pagination offset
            
        Returns
        ----
        Tuple[List[Dict], int]
            (results, total_count)
        """
        return self.db.search_with_snippets(query, limit, offset)
    
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

