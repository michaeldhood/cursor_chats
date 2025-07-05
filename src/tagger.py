"""
Module for tagging and categorizing chat conversations.
"""
import re
import json
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TagManager:
    """Manages tags for chat conversations."""
    
    def __init__(self, tags_file: Optional[str] = None):
        """
        Initialize the TagManager.
        
        Args:
            tags_file: Path to store persistent tags (JSON file)
        """
        self.tags_file = tags_file
        self.tags_data: Dict[str, List[str]] = {}
        self.tag_patterns: Dict[str, List[re.Pattern]] = self._initialize_patterns()
        
        if self.tags_file and Path(self.tags_file).exists():
            self._load_tags()
    
    def _initialize_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Initialize regex patterns for automatic tagging."""
        patterns = {
            'language': [
                re.compile(r'\b(python|py)\b', re.IGNORECASE),
                re.compile(r'\b(javascript|js|node)\b', re.IGNORECASE),
                re.compile(r'\b(typescript|ts)\b', re.IGNORECASE),
                re.compile(r'\b(java|jvm)\b', re.IGNORECASE),
                re.compile(r'\b(c\+\+|cpp|c\b)', re.IGNORECASE),
                re.compile(r'\b(rust|rs)\b', re.IGNORECASE),
                re.compile(r'\b(go|golang)\b', re.IGNORECASE),
                re.compile(r'\b(ruby|rb)\b', re.IGNORECASE),
                re.compile(r'\b(php)\b', re.IGNORECASE),
                re.compile(r'\b(swift)\b', re.IGNORECASE),
            ],
            'framework': [
                re.compile(r'\b(react|reactjs)\b', re.IGNORECASE),
                re.compile(r'\b(vue|vuejs)\b', re.IGNORECASE),
                re.compile(r'\b(angular)\b', re.IGNORECASE),
                re.compile(r'\b(django)\b', re.IGNORECASE),
                re.compile(r'\b(flask)\b', re.IGNORECASE),
                re.compile(r'\b(express|expressjs)\b', re.IGNORECASE),
                re.compile(r'\b(spring)\b', re.IGNORECASE),
                re.compile(r'\b(rails|ruby on rails)\b', re.IGNORECASE),
                re.compile(r'\b(fastapi)\b', re.IGNORECASE),
                re.compile(r'\b(nextjs|next\.js)\b', re.IGNORECASE),
            ],
            'topic': [
                re.compile(r'\b(api|rest|graphql)\b', re.IGNORECASE),
                re.compile(r'\b(database|sql|nosql|mongodb|postgres|mysql)\b', re.IGNORECASE),
                re.compile(r'\b(testing|test|unit test|integration test)\b', re.IGNORECASE),
                re.compile(r'\b(docker|container|kubernetes|k8s)\b', re.IGNORECASE),
                re.compile(r'\b(git|github|gitlab|version control)\b', re.IGNORECASE),
                re.compile(r'\b(ci/cd|continuous integration|deployment)\b', re.IGNORECASE),
                re.compile(r'\b(security|authentication|authorization|oauth)\b', re.IGNORECASE),
                re.compile(r'\b(performance|optimization|profiling)\b', re.IGNORECASE),
                re.compile(r'\b(debugging|bug|error|exception)\b', re.IGNORECASE),
                re.compile(r'\b(refactor|refactoring|code review)\b', re.IGNORECASE),
            ],
            'ai': [
                re.compile(r'\b(machine learning|ml|deep learning|neural network)\b', re.IGNORECASE),
                re.compile(r'\b(llm|large language model|gpt|claude|openai)\b', re.IGNORECASE),
                re.compile(r'\b(nlp|natural language processing)\b', re.IGNORECASE),
                re.compile(r'\b(computer vision|cv|image processing)\b', re.IGNORECASE),
            ]
        }
        return patterns
    
    def _load_tags(self) -> None:
        """Load tags from persistent storage."""
        try:
            with open(self.tags_file, 'r') as f:
                self.tags_data = json.load(f)
            logger.debug("Loaded tags from %s", self.tags_file)
        except Exception as e:
            logger.error("Error loading tags: %s", e)
            self.tags_data = {}
    
    def _save_tags(self) -> None:
        """Save tags to persistent storage."""
        if self.tags_file:
            try:
                with open(self.tags_file, 'w') as f:
                    json.dump(self.tags_data, f, indent=2)
                logger.debug("Saved tags to %s", self.tags_file)
            except Exception as e:
                logger.error("Error saving tags: %s", e)
    
    def normalize_tag(self, tag: str) -> str:
        """
        Normalize a tag to standard format.
        
        Args:
            tag: Raw tag string
            
        Returns:
            Normalized tag (lowercase, spaces replaced with hyphens)
        """
        return tag.lower().strip().replace(' ', '-')
    
    def auto_tag(self, content: str) -> Set[str]:
        """
        Automatically generate tags based on content patterns.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Set of automatically generated tags
        """
        tags = set()
        
        for category, patterns in self.tag_patterns.items():
            for pattern in patterns:
                if pattern.search(content):
                    # Extract the matched text and create a hierarchical tag
                    match = pattern.search(content)
                    if match:
                        matched_text = self.normalize_tag(match.group(0))
                        tags.add(f"{category}/{matched_text}")
        
        return tags
    
    def suggest_tags(self, content: str, existing_tags: Optional[List[str]] = None) -> List[str]:
        """
        Suggest tags based on content and existing tags.
        
        Args:
            content: Text content to analyze
            existing_tags: Already applied tags
            
        Returns:
            List of suggested tags
        """
        auto_tags = self.auto_tag(content)
        existing_set = set(existing_tags or [])
        
        # Get new suggestions not already applied
        suggestions = list(auto_tags - existing_set)
        
        # Sort by category and tag name
        suggestions.sort()
        
        return suggestions[:10]  # Limit to top 10 suggestions
    
    def add_tags(self, chat_id: str, tags: List[str]) -> None:
        """
        Add tags to a chat.
        
        Args:
            chat_id: Unique identifier for the chat
            tags: List of tags to add
        """
        if chat_id not in self.tags_data:
            self.tags_data[chat_id] = []
        
        # Normalize and add unique tags
        for tag in tags:
            normalized = self.normalize_tag(tag)
            if normalized not in self.tags_data[chat_id]:
                self.tags_data[chat_id].append(normalized)
        
        self._save_tags()
    
    def remove_tags(self, chat_id: str, tags: List[str]) -> None:
        """
        Remove tags from a chat.
        
        Args:
            chat_id: Unique identifier for the chat
            tags: List of tags to remove
        """
        if chat_id in self.tags_data:
            normalized_tags = [self.normalize_tag(tag) for tag in tags]
            self.tags_data[chat_id] = [
                t for t in self.tags_data[chat_id] 
                if t not in normalized_tags
            ]
            
            # Remove empty entries
            if not self.tags_data[chat_id]:
                del self.tags_data[chat_id]
            
            self._save_tags()
    
    def get_tags(self, chat_id: str) -> List[str]:
        """
        Get all tags for a chat.
        
        Args:
            chat_id: Unique identifier for the chat
            
        Returns:
            List of tags for the chat
        """
        return self.tags_data.get(chat_id, [])
    
    def get_all_tags(self) -> Dict[str, int]:
        """
        Get all unique tags with their frequency.
        
        Returns:
            Dictionary mapping tags to their occurrence count
        """
        tag_counts = {}
        for tags in self.tags_data.values():
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return tag_counts
    
    def find_chats_by_tag(self, tag: str) -> List[str]:
        """
        Find all chats with a specific tag.
        
        Args:
            tag: Tag to search for (supports wildcards with *)
            
        Returns:
            List of chat IDs with the tag
        """
        normalized_tag = self.normalize_tag(tag)
        matching_chats = []
        
        # Support wildcard matching
        if '*' in normalized_tag:
            pattern = re.compile(normalized_tag.replace('*', '.*'))
            for chat_id, tags in self.tags_data.items():
                if any(pattern.match(t) for t in tags):
                    matching_chats.append(chat_id)
        else:
            # Exact match
            for chat_id, tags in self.tags_data.items():
                if normalized_tag in tags:
                    matching_chats.append(chat_id)
        
        return matching_chats
    
    def merge_tags(self, old_tag: str, new_tag: str) -> int:
        """
        Merge one tag into another.
        
        Args:
            old_tag: Tag to be replaced
            new_tag: Tag to replace with
            
        Returns:
            Number of chats affected
        """
        old_normalized = self.normalize_tag(old_tag)
        new_normalized = self.normalize_tag(new_tag)
        affected_count = 0
        
        for chat_id, tags in self.tags_data.items():
            if old_normalized in tags:
                tags.remove(old_normalized)
                if new_normalized not in tags:
                    tags.append(new_normalized)
                affected_count += 1
        
        if affected_count > 0:
            self._save_tags()
        
        return affected_count
    
    def bulk_tag(self, chat_ids: List[str], tags: List[str]) -> None:
        """
        Apply tags to multiple chats at once.
        
        Args:
            chat_ids: List of chat IDs to tag
            tags: List of tags to apply
        """
        for chat_id in chat_ids:
            self.add_tags(chat_id, tags)