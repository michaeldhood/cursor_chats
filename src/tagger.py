"""
Tag Manager
===========

Manages tags for chat conversations using a standardized tag registry.

Uses the tag registry for alias resolution, pattern matching, and validation.
Tags are stored in the database via ChatDatabase.
"""
import re
import json
from typing import List, Dict, Set, Optional
from pathlib import Path
import logging

from src.core.tag_registry import TagRegistry, TAG_REGISTRY

logger = logging.getLogger(__name__)


class TagManager:
    """
    Manages tags for chat conversations using a standardized registry.
    
    Integrates with ChatDatabase for persistent storage and uses TagRegistry
    for alias resolution and pattern matching.
    """
    
    def __init__(self, db=None, registry: Optional[TagRegistry] = None):
        """
        Initialize the TagManager.
        
        Parameters
        ----
        db : ChatDatabase, optional
            Database instance for tag storage. If None, tags are managed in-memory only.
        registry : TagRegistry, optional
            Tag registry instance. If None, creates a new registry with default tags.
        """
        self.db = db
        self.registry = registry or TagRegistry(TAG_REGISTRY)
        
        # In-memory cache for tags (used when db is None)
        self.tags_cache: Dict[int, List[str]] = {}
    
    def resolve_alias(self, raw_tag: str) -> Optional[str]:
        """
        Resolve a tag alias to its canonical form.
        
        Parameters
        ----
        raw_tag : str
            Raw tag string (may be alias or canonical)
            
        Returns
        ----
        str, optional
            Canonical tag in format "dimension/tag", or None if not found
        """
        return self.registry.resolve_alias(raw_tag)
    
    def normalize_tag(self, tag: str) -> str:
        """
        Normalize a tag to standard format and resolve aliases.
        
        Parameters
        ----
        tag : str
            Raw tag string
            
        Returns
        ----
        str
            Canonical tag if found, otherwise normalized version of input
        """
        # Try to resolve alias first
        canonical = self.registry.resolve_alias(tag)
        if canonical:
            return canonical
        
        # If not found in registry, normalize and return
        # Unknown tags are kept as-is (may be custom tags)
        return tag.lower().strip().replace(' ', '-')
    
    def auto_tag(self, content: str, file_extensions: Optional[List[str]] = None,
                 chat_mode: Optional[str] = None) -> Set[str]:
        """
        Automatically generate tags based on content, file extensions, and chat mode.
        
        Parameters
        ----
        content : str
            Text content to analyze
        file_extensions : List[str], optional
            List of file extensions (e.g., [".py", ".js"])
        chat_mode : str, optional
            Chat mode (e.g., "debug", "edit")
            
        Returns
        ----
        Set[str]
            Set of automatically generated canonical tags
        """
        tags = set()
        
        # Match patterns in content
        tags.update(self.registry.match_patterns(content))
        
        # Match file extensions
        if file_extensions:
            tags.update(self.registry.get_file_extension_tags(file_extensions))
        
        # Match chat mode
        if chat_mode:
            tags.update(self.registry.get_chat_mode_tags(chat_mode))
        
        return tags
    
    def add_tags(self, chat_id: int, tags: List[str]) -> None:
        """
        Add tags to a chat.
        
        Parameters
        ----
        chat_id : int
            Chat ID (database ID, not composer ID)
        tags : List[str]
            List of tags to add (will be normalized and aliases resolved)
        """
        # Normalize and resolve aliases
        normalized_tags = []
        for tag in tags:
            normalized = self.normalize_tag(tag)
            if normalized:
                normalized_tags.append(normalized)
        
        if not normalized_tags:
            return
        
        if self.db:
            # Store in database
            self.db.add_tags(chat_id, normalized_tags)
        else:
            # Store in memory cache
            if chat_id not in self.tags_cache:
                self.tags_cache[chat_id] = []
            for tag in normalized_tags:
                if tag not in self.tags_cache[chat_id]:
                    self.tags_cache[chat_id].append(tag)
    
    def remove_tags(self, chat_id: int, tags: List[str]) -> None:
        """
        Remove tags from a chat.
        
        Parameters
        ----
        chat_id : int
            Chat ID
        tags : List[str]
            List of tags to remove
        """
        # Normalize tags
        normalized_tags = [self.normalize_tag(tag) for tag in tags]
        
        if self.db:
            self.db.remove_tags(chat_id, normalized_tags)
        else:
            if chat_id in self.tags_cache:
                self.tags_cache[chat_id] = [
                    t for t in self.tags_cache[chat_id] 
                    if t not in normalized_tags
                ]
    
    def get_tags(self, chat_id: int) -> List[str]:
        """
        Get all tags for a chat.
        
        Parameters
        ----
        chat_id : int
            Chat ID
            
        Returns
        ----
        List[str]
            List of tags for the chat
        """
        if self.db:
            return self.db.get_chat_tags(chat_id)
        else:
            return self.tags_cache.get(chat_id, [])
    
    def get_all_tags(self) -> Dict[str, int]:
        """
        Get all unique tags with their frequency.
        
        Returns
        ----
        Dict[str, int]
            Dictionary mapping tags to their occurrence count
        """
        if self.db:
            return self.db.get_all_tags()
        else:
            # Count from cache
            tag_counts = {}
            for tags in self.tags_cache.values():
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            return tag_counts
    
    def find_chats_by_tag(self, tag: str) -> List[int]:
        """
        Find all chats with a specific tag.
        
        Parameters
        ----
        tag : str
            Tag to search for (supports SQL LIKE wildcards: %)
            
        Returns
        ----
        List[int]
            List of chat IDs with the tag
        """
        if self.db:
            return self.db.find_chats_by_tag(tag)
        else:
            # Search in cache
            normalized_tag = self.normalize_tag(tag)
            matching_chats = []
            for chat_id, tags in self.tags_cache.items():
                if normalized_tag in tags:
                    matching_chats.append(chat_id)
            return matching_chats
    
    def validate_tag(self, tag: str) -> bool:
        """
        Validate that a tag exists in the registry.
        
        Parameters
        ----
        tag : str
            Tag to validate (can be alias or canonical)
            
        Returns
        ----
        bool
            True if tag is valid, False otherwise
        """
        return self.registry.validate_tag(tag)
    
    def suggest_tags(self, content: str, existing_tags: Optional[List[str]] = None,
                    file_extensions: Optional[List[str]] = None,
                    chat_mode: Optional[str] = None) -> List[str]:
        """
        Suggest tags based on content, file extensions, and chat mode.
        
        Parameters
        ----
        content : str
            Text content to analyze
        existing_tags : List[str], optional
            Already applied tags
        file_extensions : List[str], optional
            List of file extensions
        chat_mode : str, optional
            Chat mode
            
        Returns
        ----
        List[str]
            List of suggested tags (top 10, excluding existing)
        """
        auto_tags = self.auto_tag(content, file_extensions, chat_mode)
        existing_set = set(existing_tags or [])
        
        # Get new suggestions not already applied
        suggestions = list(auto_tags - existing_set)
        
        # Sort by dimension and tag name
        suggestions.sort()
        
        return suggestions[:10]  # Limit to top 10 suggestions
