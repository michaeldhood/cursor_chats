"""
Tests for aggregator workspace linking and title enrichment.
"""
import pytest
import tempfile
import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime

from src.core.db import ChatDatabase
from src.core.models import Chat, Message, Workspace, ChatMode, MessageRole
from src.readers.workspace_reader import WorkspaceStateReader
from src.readers.global_reader import GlobalComposerReader
from src.services.aggregator import ChatAggregator


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    db = ChatDatabase(path)
    yield db
    db.close()
    os.unlink(path)


@pytest.fixture
def temp_workspace_storage(tmp_path):
    """Create a temporary workspace storage structure."""
    workspace_hash = "test-workspace-123"
    workspace_dir = tmp_path / workspace_hash
    workspace_dir.mkdir()
    
    # Create state.vscdb
    db_path = workspace_dir / "state.vscdb"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
    
    # Add composer.composerData with composer heads
    composer_data = {
        "allComposers": [
            {
                "composerId": "composer-abc-123",
                "name": "Test Chat Name",
                "subtitle": "Test Subtitle",
                "createdAt": 1734000000000,
                "lastUpdatedAt": 1734001000000,
                "unifiedMode": "chat",
                "forceMode": "chat",
            }
        ]
    }
    cursor.execute("INSERT INTO ItemTable (key, value) VALUES (?, ?)",
                   ("composer.composerData", json.dumps(composer_data)))
    
    conn.commit()
    conn.close()
    
    # Create workspace.json
    workspace_json = workspace_dir / "workspace.json"
    workspace_json.write_text(json.dumps({"folder": "file:///test/project/path"}))
    
    yield tmp_path, workspace_hash


@pytest.fixture
def temp_global_db():
    """Create a temporary global database with composer data."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    # Match real Cursor DB schema: key is TEXT with UNIQUE constraint (creates index)
    cursor.execute("CREATE TABLE cursorDiskKV (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)")
    
    # Insert composer data
    composer_id = "composer-abc-123"
    key = f"composerData:{composer_id}"  # TEXT, not bytes
    value = json.dumps({
        "composerId": composer_id,
        "conversation": [
            {
                "type": 1,
                "bubbleId": "bubble-1",
                "text": "Hello",
            },
            {
                "type": 2,
                "bubbleId": "bubble-2",
                "text": "Hi there!",
            },
        ],
    }).encode('utf-8')
    
    cursor.execute("INSERT INTO cursorDiskKV (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
    
    yield Path(path)
    os.unlink(path)


def test_workspace_reader_composer_ids(temp_workspace_storage):
    """Test that workspace reader extracts composer IDs correctly."""
    storage_path, workspace_hash = temp_workspace_storage
    reader = WorkspaceStateReader(workspace_storage_path=storage_path)
    
    composer_ids = reader.get_composer_ids_for_workspace(workspace_hash)
    assert len(composer_ids) == 1
    assert "composer-abc-123" in composer_ids


def test_workspace_reader_composer_heads(temp_workspace_storage):
    """Test that workspace reader extracts composer heads."""
    storage_path, workspace_hash = temp_workspace_storage
    reader = WorkspaceStateReader(workspace_storage_path=storage_path)
    
    heads = reader.get_composer_heads_for_workspace(workspace_hash)
    assert len(heads) == 1
    assert "composer-abc-123" in heads
    assert heads["composer-abc-123"]["name"] == "Test Chat Name"
    assert heads["composer-abc-123"]["subtitle"] == "Test Subtitle"


def test_aggregator_title_enrichment(temp_db, temp_workspace_storage, temp_global_db):
    """Test that aggregator enriches titles from workspace metadata."""
    storage_path, workspace_hash = temp_workspace_storage
    
    # Mock the readers
    class MockWorkspaceReader:
        def __init__(self, storage_path):
            self.workspace_storage_path = storage_path
        
        def read_all_workspaces(self):
            reader = WorkspaceStateReader(workspace_storage_path=storage_path)
            return reader.read_all_workspaces()
        
        def get_composer_ids_for_workspace(self, hash):
            reader = WorkspaceStateReader(workspace_storage_path=storage_path)
            return reader.get_composer_ids_for_workspace(hash)
        
        def get_composer_heads_for_workspace(self, hash):
            reader = WorkspaceStateReader(workspace_storage_path=storage_path)
            return reader.get_composer_heads_for_workspace(hash)
    
    class MockGlobalReader:
        def __init__(self, db_path):
            self.db_path = db_path
        
        def read_all_composers(self):
            reader = GlobalComposerReader(global_storage_path=self.db_path.parent)
            reader.db_path = self.db_path
            return reader.read_all_composers()
    
    aggregator = ChatAggregator(temp_db)
    aggregator.workspace_reader = MockWorkspaceReader(storage_path)
    aggregator.global_reader = MockGlobalReader(temp_global_db)
    
    # Ingest
    stats = aggregator.ingest_all()
    assert stats["ingested"] == 1
    
    # Check that chat has enriched title
    chats = temp_db.list_chats()
    assert len(chats) == 1
    assert chats[0]["title"] == "Test Chat Name"  # From workspace head, not "Untitled Chat"


def test_aggregator_workspace_linking(temp_db, temp_workspace_storage, temp_global_db):
    """Test that aggregator correctly links composers to workspaces."""
    storage_path, workspace_hash = temp_workspace_storage
    
    # Create workspace in DB first
    workspace = Workspace(
        workspace_hash=workspace_hash,
        folder_uri="file:///test/project/path",
        resolved_path="/test/project/path",
    )
    workspace_id = temp_db.upsert_workspace(workspace)
    
    # Mock readers
    class MockWorkspaceReader:
        def __init__(self, storage_path):
            self.workspace_storage_path = storage_path
        
        def read_all_workspaces(self):
            reader = WorkspaceStateReader(workspace_storage_path=storage_path)
            return reader.read_all_workspaces()
        
        def get_composer_ids_for_workspace(self, hash):
            reader = WorkspaceStateReader(workspace_storage_path=storage_path)
            return reader.get_composer_ids_for_workspace(hash)
        
        def get_composer_heads_for_workspace(self, hash):
            reader = WorkspaceStateReader(workspace_storage_path=storage_path)
            return reader.get_composer_heads_for_workspace(hash)
    
    class MockGlobalReader:
        def __init__(self, db_path):
            self.db_path = db_path
        
        def read_all_composers(self):
            reader = GlobalComposerReader(global_storage_path=self.db_path.parent)
            reader.db_path = self.db_path
            return reader.read_all_composers()
    
    aggregator = ChatAggregator(temp_db)
    aggregator.workspace_reader = MockWorkspaceReader(storage_path)
    aggregator.global_reader = MockGlobalReader(temp_global_db)
    
    # Ingest
    stats = aggregator.ingest_all()
    assert stats["ingested"] == 1
    
    # Check that chat is linked to workspace
    chats = temp_db.list_chats()
    assert len(chats) == 1
    # Workspace path comes from workspace.json folder URI
    assert chats[0].get("workspace_path") == "file:///test/project/path"


def test_db_count_methods(temp_db):
    """Test database count methods."""
    # Create test data
    workspace = Workspace(workspace_hash="test123")
    workspace_id = temp_db.upsert_workspace(workspace)
    
    for i in range(5):
        chat = Chat(
            cursor_composer_id=f"composer-{i}",
            workspace_id=workspace_id,
            title=f"Chat {i}",
            messages=[
                Message(role=MessageRole.USER, text=f"Message {i}"),
            ],
        )
        temp_db.upsert_chat(chat)
    
    # Test count_chats
    total = temp_db.count_chats()
    assert total == 5
    
    workspace_count = temp_db.count_chats(workspace_id)
    assert workspace_count == 5
    
    # Test count_search
    search_count = temp_db.count_search("Message")
    assert search_count == 5
    
    # FTS5 search - use a more specific query
    search_count_specific = temp_db.count_search('"Message 3"')  # Exact phrase
    assert search_count_specific >= 1  # At least one match

