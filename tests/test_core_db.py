"""
Tests for core database layer.
"""
import pytest
import tempfile
import os
from datetime import datetime

from src.core.db import ChatDatabase
from src.core.models import Chat, Message, Workspace, ChatMode, MessageRole


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    db = ChatDatabase(path)
    yield db
    db.close()
    os.unlink(path)


def test_workspace_upsert(temp_db):
    """Test workspace upsert functionality."""
    workspace = Workspace(
        workspace_hash="test123",
        folder_uri="file:///test/path",
        resolved_path="/test/path",
    )
    
    workspace_id = temp_db.upsert_workspace(workspace)
    assert workspace_id is not None
    
    # Upsert again should return same ID
    workspace_id2 = temp_db.upsert_workspace(workspace)
    assert workspace_id == workspace_id2


def test_chat_upsert(temp_db):
    """Test chat upsert functionality."""
    # Create workspace first
    workspace = Workspace(workspace_hash="test123")
    workspace_id = temp_db.upsert_workspace(workspace)
    
    # Create chat
    chat = Chat(
        cursor_composer_id="composer-123",
        workspace_id=workspace_id,
        title="Test Chat",
        mode=ChatMode.CHAT,
        created_at=datetime.now(),
        messages=[
            Message(
                role=MessageRole.USER,
                text="Hello",
                created_at=datetime.now(),
            ),
            Message(
                role=MessageRole.ASSISTANT,
                text="Hi there!",
                created_at=datetime.now(),
            ),
        ],
    )
    
    chat_id = temp_db.upsert_chat(chat)
    assert chat_id is not None
    
    # Retrieve chat
    retrieved = temp_db.get_chat(chat_id)
    assert retrieved is not None
    assert retrieved["title"] == "Test Chat"
    assert len(retrieved["messages"]) == 2


def test_search(temp_db):
    """Test full-text search."""
    # Create test chat
    workspace = Workspace(workspace_hash="test123")
    workspace_id = temp_db.upsert_workspace(workspace)
    
    chat = Chat(
        cursor_composer_id="composer-123",
        workspace_id=workspace_id,
        title="Python Chat",
        messages=[
            Message(
                role=MessageRole.USER,
                text="How do I use Python?",
            ),
            Message(
                role=MessageRole.ASSISTANT,
                text="Python is a programming language...",
            ),
        ],
    )
    temp_db.upsert_chat(chat)
    
    # Search
    results = temp_db.search_chats("Python")
    assert len(results) > 0
    assert any(r["title"] == "Python Chat" for r in results)


def test_list_chats(temp_db):
    """Test listing chats."""
    workspace = Workspace(workspace_hash="test123")
    workspace_id = temp_db.upsert_workspace(workspace)
    
    # Create multiple chats
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
    
    chats = temp_db.list_chats(limit=10)
    assert len(chats) == 5

