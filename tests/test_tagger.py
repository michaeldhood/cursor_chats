"""
Test cases for the tagging system (CUR-5).

Tests the new registry-based TagManager with canonical tag format.
"""
import pytest

from src.tagger import TagManager


class TestTagManager:
    """Test the TagManager class functionality with new registry-based API."""
    
    def test_normalize_tag_with_alias(self):
        """Test tag normalization with alias resolution."""
        tag_manager = TagManager()
        
        # Test alias resolution to canonical form
        assert tag_manager.normalize_tag("py") == "tech/python"
        assert tag_manager.normalize_tag("js") == "tech/javascript"
        assert tag_manager.normalize_tag("ts") == "tech/typescript"
        assert tag_manager.normalize_tag("node") == "tech/javascript"
        assert tag_manager.normalize_tag("debug") == "activity/debugging"
        
        # Test canonical tags pass through
        assert tag_manager.normalize_tag("tech/python") == "tech/python"
        assert tag_manager.normalize_tag("activity/debugging") == "activity/debugging"
    
    def test_normalize_tag_unknown(self):
        """Test normalization of unknown tags."""
        tag_manager = TagManager()
        
        # Unknown tags get normalized to lowercase with hyphens
        assert tag_manager.normalize_tag("My Custom Tag") == "my-custom-tag"
        assert tag_manager.normalize_tag("  React JS  ") == "react-js"
        assert tag_manager.normalize_tag("Machine Learning") == "machine-learning"
        assert tag_manager.normalize_tag("CI/CD") == "ci/cd"
    
    def test_auto_tag_from_content(self):
        """Test automatic tag detection from content patterns."""
        tag_manager = TagManager()
        
        # Test Python detection (matches import patterns)
        content = "import pandas as pd\nfrom pathlib import Path\ndef my_function():"
        tags = tag_manager.auto_tag(content)
        assert "tech/python" in tags
        
        # Test JavaScript detection (matches code patterns)
        content = "const myVar = 42\nfunction myFunc() {}\nimport React from 'react'"
        tags = tag_manager.auto_tag(content)
        assert "tech/javascript" in tags
        assert "tech/react" in tags
        
        # Test TypeScript detection (matches type patterns)
        content = "interface MyType {\n  value: string\n}\ntype MyAlias = string"
        tags = tag_manager.auto_tag(content)
        assert "tech/typescript" in tags
        
        # Test framework detection
        content = "from fastapi import FastAPI\n@app.get('/')"
        tags = tag_manager.auto_tag(content)
        assert "tech/fastapi" in tags
    
    def test_auto_tag_from_file_extensions(self):
        """Test automatic tag detection from file extensions."""
        tag_manager = TagManager()
        
        # Test Python file extension
        tags = tag_manager.auto_tag("", file_extensions=[".py"])
        assert "tech/python" in tags
        
        # Test JavaScript file extension
        tags = tag_manager.auto_tag("", file_extensions=[".js"])
        assert "tech/javascript" in tags
        
        # Test TypeScript file extension
        tags = tag_manager.auto_tag("", file_extensions=[".ts", ".tsx"])
        assert "tech/typescript" in tags
        
        # Test multiple extensions
        tags = tag_manager.auto_tag("", file_extensions=[".py", ".js"])
        assert "tech/python" in tags
        assert "tech/javascript" in tags
    
    def test_auto_tag_from_chat_mode(self):
        """Test automatic tag detection from chat mode."""
        tag_manager = TagManager()
        
        # Test debug mode
        tags = tag_manager.auto_tag("", chat_mode="debug")
        assert "activity/debugging" in tags
        
        # Test with content and mode
        tags = tag_manager.auto_tag("Fixing a bug", chat_mode="debug")
        assert "activity/debugging" in tags
    
    def test_add_and_get_tags_in_memory(self):
        """Test adding and retrieving tags using in-memory cache."""
        tag_manager = TagManager(db=None)  # Explicitly use in-memory mode
        
        # Add tags with int chat_id
        # Note: "testing" gets normalized to "activity/testing" via alias resolution
        tag_manager.add_tags(1, ["tech/python", "topic/api", "testing"])
        tags = tag_manager.get_tags(1)
        
        assert "tech/python" in tags
        assert "topic/api" in tags
        assert "activity/testing" in tags  # "testing" is an alias for "activity/testing"
        
        # Add duplicate tag (should not add)
        tag_manager.add_tags(1, ["tech/python", "topic/database"])
        tags = tag_manager.get_tags(1)
        
        assert "tech/python" in tags
        assert "topic/api" in tags
        assert "activity/testing" in tags  # Normalized from "testing"
        assert "topic/database" in tags
        # Should not have duplicates
        assert tags.count("tech/python") == 1
        
        # Test alias resolution during add
        tag_manager.add_tags(2, ["py", "js"])  # Aliases
        tags = tag_manager.get_tags(2)
        assert "tech/python" in tags
        assert "tech/javascript" in tags
    
    def test_remove_tags_in_memory(self):
        """Test removing tags from in-memory cache."""
        tag_manager = TagManager(db=None)
        
        tag_manager.add_tags(1, ["tech/python", "topic/api", "testing", "topic/database"])
        tag_manager.remove_tags(1, ["topic/api", "testing"])
        
        tags = tag_manager.get_tags(1)
        assert "tech/python" in tags
        assert "topic/database" in tags
        assert "topic/api" not in tags
        assert "testing" not in tags
        
        # Remove all tags
        tag_manager.remove_tags(1, ["tech/python", "topic/database"])
        tags = tag_manager.get_tags(1)
        assert tags == []
    
    def test_get_all_tags_with_counts(self):
        """Test getting all tags with frequency counts."""
        tag_manager = TagManager(db=None)
        
        tag_manager.add_tags(1, ["tech/python", "topic/api"])
        tag_manager.add_tags(2, ["tech/python", "topic/database"])
        tag_manager.add_tags(3, ["tech/javascript", "topic/api"])
        
        all_tags = tag_manager.get_all_tags()
        
        assert all_tags["tech/python"] == 2
        assert all_tags["topic/api"] == 2
        assert all_tags["topic/database"] == 1
        assert all_tags["tech/javascript"] == 1
    
    def test_find_chats_by_tag_in_memory(self):
        """Test finding chats by tag in in-memory cache."""
        tag_manager = TagManager(db=None)
        
        tag_manager.add_tags(1, ["tech/python", "topic/api"])
        tag_manager.add_tags(2, ["tech/javascript", "topic/api"])
        tag_manager.add_tags(3, ["tech/python", "topic/database"])
        
        # Exact match
        chats = tag_manager.find_chats_by_tag("tech/python")
        assert set(chats) == {1, 3}
        
        # Test with alias
        chats = tag_manager.find_chats_by_tag("py")
        assert set(chats) == {1, 3}  # Should resolve to tech/python
        
        # Test with canonical tag
        chats = tag_manager.find_chats_by_tag("topic/api")
        assert set(chats) == {1, 2}
    
    def test_suggest_tags_excludes_existing(self):
        """Test tag suggestions exclude already-applied tags."""
        tag_manager = TagManager()
        
        content = "Building a React app with TypeScript and testing with Jest"
        existing_tags = ["tech/react"]
        
        suggestions = tag_manager.suggest_tags(content, existing_tags=existing_tags)
        
        # Should suggest TypeScript and testing but not React (already tagged)
        assert "tech/react" not in suggestions  # Already exists
        # Note: exact suggestions depend on registry patterns, so we check structure
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 10  # Limited to top 10
        
        # Should be sorted
        assert suggestions == sorted(suggestions)
    
    def test_validate_tag(self):
        """Test tag validation against registry."""
        tag_manager = TagManager()
        
        # Valid canonical tags
        assert tag_manager.validate_tag("tech/python") is True
        assert tag_manager.validate_tag("activity/debugging") is True
        
        # Valid aliases
        assert tag_manager.validate_tag("py") is True
        assert tag_manager.validate_tag("js") is True
        assert tag_manager.validate_tag("debug") is True
        
        # Invalid tags
        assert tag_manager.validate_tag("nonexistent-tag") is False
        assert tag_manager.validate_tag("invalid/dimension/tag") is False
    
    def test_resolve_alias(self):
        """Test alias resolution to canonical form."""
        tag_manager = TagManager()
        
        # Test alias resolution
        assert tag_manager.resolve_alias("py") == "tech/python"
        assert tag_manager.resolve_alias("js") == "tech/javascript"
        assert tag_manager.resolve_alias("ts") == "tech/typescript"
        assert tag_manager.resolve_alias("debug") == "activity/debugging"
        
        # Canonical tags return as-is
        assert tag_manager.resolve_alias("tech/python") == "tech/python"
        
        # Unknown aliases return None
        assert tag_manager.resolve_alias("unknown-alias") is None
    
    def test_multiple_chats_tag_management(self):
        """Test managing tags across multiple chats."""
        tag_manager = TagManager(db=None)
        
        # Add different tags to different chats
        tag_manager.add_tags(1, ["tech/python"])
        tag_manager.add_tags(2, ["tech/javascript"])
        tag_manager.add_tags(3, ["tech/python", "tech/javascript"])
        
        # Verify each chat has correct tags
        assert tag_manager.get_tags(1) == ["tech/python"]
        assert tag_manager.get_tags(2) == ["tech/javascript"]
        assert set(tag_manager.get_tags(3)) == {"tech/python", "tech/javascript"}
        
        # Verify counts
        all_tags = tag_manager.get_all_tags()
        assert all_tags["tech/python"] == 2
        assert all_tags["tech/javascript"] == 2
