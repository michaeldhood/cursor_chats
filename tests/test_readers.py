"""
Tests for Cursor database readers.
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.readers.global_reader import GlobalComposerReader
from src.readers.workspace_reader import WorkspaceStateReader


@pytest.fixture
def temp_global_db():
    """Create a temporary global database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE cursorDiskKV (key BLOB, value BLOB)")

    # Insert test composer data
    composer_id = "test-composer-123"
    key = f"composerData:{composer_id}".encode("utf-8")
    value = json.dumps(
        {
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
        }
    ).encode("utf-8")

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


def test_global_reader_skips_null_values(temp_global_db):
    """Regression: global reader should skip cursorDiskKV rows with NULL value."""
    # Add a NULL payload row that should be ignored (Cursor can produce these).
    conn = sqlite3.connect(str(temp_global_db))
    cursor = conn.cursor()
    null_composer_id = "null-composer-456"
    null_key = f"composerData:{null_composer_id}".encode("utf-8")
    cursor.execute(
        "INSERT INTO cursorDiskKV (key, value) VALUES (?, ?)", (null_key, None)
    )
    conn.commit()
    conn.close()

    reader = GlobalComposerReader(global_storage_path=temp_global_db.parent)
    reader.db_path = temp_global_db

    composers = list(reader.read_all_composers())
    composer_ids = {c["composer_id"] for c in composers}

    assert "test-composer-123" in composer_ids
    assert null_composer_id not in composer_ids


@pytest.fixture
def temp_workspace_db():
    """Create a temporary workspace database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")

    # Insert test data
    cursor.execute(
        "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
        ("aiService.prompts", json.dumps([{"text": "test prompt", "commandType": 4}])),
    )
    cursor.execute(
        "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
        (
            "composer.composerData",
            json.dumps({"allComposers": [{"composerId": "test-123"}]}),
        ),
    )

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


def test_workspace_reader_handles_null_item_values(tmp_path):
    """Regression: workspace reader should not crash if ItemTable.value is NULL."""
    workspace_hash = "null-workspace"
    workspace_dir = tmp_path / workspace_hash
    workspace_dir.mkdir()

    db_path = workspace_dir / "state.vscdb"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
    cursor.execute(
        "INSERT INTO ItemTable (key, value) VALUES (?, ?)", ("aiService.prompts", None)
    )
    cursor.execute(
        "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
        ("aiService.generations", None),
    )
    cursor.execute(
        "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
        ("composer.composerData", None),
    )
    conn.commit()
    conn.close()

    workspace_json = workspace_dir / "workspace.json"
    workspace_json.write_text(json.dumps({"folder": "file:///null/path"}))

    reader = WorkspaceStateReader(workspace_storage_path=tmp_path)
    metadata = reader.read_workspace_metadata(workspace_hash)

    assert metadata is not None
    assert metadata["prompts"] == []
    assert metadata["generations"] == []
    assert metadata["composer_data"] is None
