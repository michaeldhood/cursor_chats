"""
Tests for Cursor database readers.
"""
import pytest
import tempfile
import sqlite3
import json
import os
from pathlib import Path

from src.readers.global_reader import GlobalComposerReader
from src.readers.workspace_reader import WorkspaceStateReader


@pytest.fixture
def temp_global_db():
    """Create a temporary global database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE cursorDiskKV (key BLOB, value BLOB)")
    
    # Insert test composer data
    composer_id = "test-composer-123"
    key = f"composerData:{composer_id}".encode('utf-8')
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


def test_global_reader(temp_global_db):
    """Test global composer reader."""
    reader = GlobalComposerReader(global_storage_path=temp_global_db.parent)
    reader.db_path = temp_global_db
    
    composers = list(reader.read_all_composers())
    assert len(composers) == 1
    assert composers[0]["composer_id"] == "test-composer-123"
    assert "conversation" in composers[0]["data"]


@pytest.fixture
def temp_workspace_db():
    """Create a temporary workspace database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
    
    # Insert test data
    cursor.execute("INSERT INTO ItemTable (key, value) VALUES (?, ?)",
                   ("aiService.prompts", json.dumps([{"text": "test prompt", "commandType": 4}])))
    cursor.execute("INSERT INTO ItemTable (key, value) VALUES (?, ?)",
                   ("composer.composerData", json.dumps({
                       "allComposers": [{"composerId": "test-123"}]
                   })))
    
    conn.commit()
    conn.close()
    
    yield Path(path)
    os.unlink(path)


def test_workspace_reader(temp_workspace_db, tmp_path):
    """Test workspace reader."""
    # Create workspace directory structure
    workspace_hash = "test-workspace"
    workspace_dir = tmp_path / workspace_hash
    workspace_dir.mkdir()
    
    # Copy database
    import shutil
    shutil.copy(temp_workspace_db, workspace_dir / "state.vscdb")
    
    # Create workspace.json
    workspace_json = workspace_dir / "workspace.json"
    workspace_json.write_text(json.dumps({"folder": "file:///test/path"}))
    
    reader = WorkspaceStateReader(workspace_storage_path=tmp_path)
    metadata = reader.read_workspace_metadata(workspace_hash)
    
    assert metadata is not None
    assert len(metadata["prompts"]) > 0
    assert metadata["composer_data"] is not None

