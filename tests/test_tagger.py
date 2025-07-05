"""
Test cases for the tagging system (CUR-5).
"""
import json
import tempfile
from pathlib import Path
import pytest

from src.tagger import TagManager


class TestTagManager:
    """Test the TagManager class functionality."""
    
    def test_normalize_tag(self):
        """Test tag normalization."""
        tag_manager = TagManager()
        
        assert tag_manager.normalize_tag("Python") == "python"
        assert tag_manager.normalize_tag("  React JS  ") == "react-js"
        assert tag_manager.normalize_tag("Machine Learning") == "machine-learning"
        assert tag_manager.normalize_tag("CI/CD") == "ci/cd"
    
    def test_auto_tag_languages(self):
        """Test automatic language detection."""
        tag_manager = TagManager()
        
        # Test Python detection
        content = "I'm writing a Python script to parse JSON files"
        tags = tag_manager.auto_tag(content)
        assert "language/python" in tags
        
        # Test JavaScript detection
        content = "This JavaScript function uses React hooks"
        tags = tag_manager.auto_tag(content)
        assert "language/javascript" in tags
        assert "framework/react" in tags
        
        # Test multiple languages
        content = "Converting from Python to TypeScript for better type safety"
        tags = tag_manager.auto_tag(content)
        assert "language/python" in tags
        assert "language/typescript" in tags
    
    def test_auto_tag_frameworks(self):
        """Test automatic framework detection."""
        tag_manager = TagManager()
        
        content = "Building a Django REST API with FastAPI endpoints"
        tags = tag_manager.auto_tag(content)
        assert "framework/django" in tags
        assert "framework/fastapi" in tags
        assert "topic/rest" in tags  # Matches "REST" from the content
    
    def test_auto_tag_topics(self):
        """Test automatic topic detection."""
        tag_manager = TagManager()
        
        content = "Debugging database performance issues in PostgreSQL"
        tags = tag_manager.auto_tag(content)
        assert "topic/debugging" in tags
        assert "topic/database" in tags
        assert "topic/performance" in tags
    
    def test_add_and_get_tags(self):
        """Test adding and retrieving tags."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tags_file = f.name
        
        try:
            tag_manager = TagManager(tags_file)
            
            # Add tags
            tag_manager.add_tags("chat1", ["python", "api", "testing"])
            tags = tag_manager.get_tags("chat1")
            
            assert set(tags) == {"python", "api", "testing"}
            
            # Add duplicate tag (should not add)
            tag_manager.add_tags("chat1", ["python", "database"])
            tags = tag_manager.get_tags("chat1")
            
            assert set(tags) == {"python", "api", "testing", "database"}
            
            # Verify persistence
            tag_manager2 = TagManager(tags_file)
            tags = tag_manager2.get_tags("chat1")
            assert set(tags) == {"python", "api", "testing", "database"}
            
        finally:
            Path(tags_file).unlink(missing_ok=True)
    
    def test_remove_tags(self):
        """Test removing tags."""
        tag_manager = TagManager()
        
        tag_manager.add_tags("chat1", ["python", "api", "testing", "database"])
        tag_manager.remove_tags("chat1", ["api", "testing"])
        
        tags = tag_manager.get_tags("chat1")
        assert set(tags) == {"python", "database"}
        
        # Remove all tags
        tag_manager.remove_tags("chat1", ["python", "database"])
        tags = tag_manager.get_tags("chat1")
        assert tags == []
    
    def test_find_chats_by_tag(self):
        """Test finding chats by tag."""
        tag_manager = TagManager()
        
        tag_manager.add_tags("chat1", ["language/python", "topic/api"])
        tag_manager.add_tags("chat2", ["language/javascript", "topic/api"])
        tag_manager.add_tags("chat3", ["language/python", "topic/database"])
        
        # Exact match
        chats = tag_manager.find_chats_by_tag("language/python")
        assert set(chats) == {"chat1", "chat3"}
        
        # Wildcard match
        chats = tag_manager.find_chats_by_tag("language/*")
        assert set(chats) == {"chat1", "chat2", "chat3"}
        
        chats = tag_manager.find_chats_by_tag("*/api")
        assert set(chats) == {"chat1", "chat2"}
    
    def test_get_all_tags(self):
        """Test getting all tags with counts."""
        tag_manager = TagManager()
        
        tag_manager.add_tags("chat1", ["python", "api"])
        tag_manager.add_tags("chat2", ["python", "database"])
        tag_manager.add_tags("chat3", ["javascript", "api"])
        
        all_tags = tag_manager.get_all_tags()
        
        assert all_tags == {
            "python": 2,
            "api": 2,
            "database": 1,
            "javascript": 1
        }
    
    def test_merge_tags(self):
        """Test merging tags."""
        tag_manager = TagManager()
        
        tag_manager.add_tags("chat1", ["js", "python"])
        tag_manager.add_tags("chat2", ["js", "database"])
        tag_manager.add_tags("chat3", ["javascript", "api"])
        
        # Merge js -> javascript
        affected = tag_manager.merge_tags("js", "javascript")
        assert affected == 2
        
        # Check results
        assert "javascript" in tag_manager.get_tags("chat1")
        assert "javascript" in tag_manager.get_tags("chat2")
        assert "js" not in tag_manager.get_tags("chat1")
        assert "js" not in tag_manager.get_tags("chat2")
    
    def test_bulk_tag(self):
        """Test bulk tagging."""
        tag_manager = TagManager()
        
        chat_ids = ["chat1", "chat2", "chat3"]
        tags = ["project/important", "needs-review"]
        
        tag_manager.bulk_tag(chat_ids, tags)
        
        for chat_id in chat_ids:
            chat_tags = tag_manager.get_tags(chat_id)
            assert "project/important" in chat_tags
            assert "needs-review" in chat_tags
    
    def test_suggest_tags(self):
        """Test tag suggestions."""
        tag_manager = TagManager()
        
        content = "Building a React app with TypeScript and testing with Jest"
        existing_tags = ["framework/react"]
        
        suggestions = tag_manager.suggest_tags(content, existing_tags)
        
        # Should suggest TypeScript and testing but not React (already tagged)
        assert "language/typescript" in suggestions
        assert "topic/testing" in suggestions
        assert "framework/react" not in suggestions  # Already exists
        
        # Should be sorted
        assert suggestions == sorted(suggestions)