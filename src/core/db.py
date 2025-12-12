"""
Database layer for chat aggregation.

Provides SQLite database with FTS5 full-text search capabilities.
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import os
import platform

from src.core.models import Chat, Message, Workspace, ChatMode, MessageRole

logger = logging.getLogger(__name__)


def get_default_db_path() -> Path:
    """
    Get the default database path based on OS.
    
    Returns
    ----
    Path
        Default path to chats.db
    """
    system = platform.system()
    home = Path.home()
    
    if system == 'Darwin':  # macOS
        base_dir = home / "Library" / "Application Support" / "cursor-chats"
    elif system == 'Windows':
        base_dir = home / "AppData" / "Roaming" / "cursor-chats"
    elif system == 'Linux':
        base_dir = home / ".local" / "share" / "cursor-chats"
    else:
        base_dir = home / ".cursor-chats"
    
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "chats.db"


class ChatDatabase:
    """
    SQLite database for storing aggregated chat data.
    
    Provides methods for storing and querying chats, messages, and workspaces
    with full-text search capabilities via FTS5.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Parameters
        ----
        db_path : str, optional
            Path to database file. If None, uses default OS-specific location.
        """
        if db_path is None:
            db_path = str(get_default_db_path())
        
        self.db_path = db_path
        self.conn = None
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Create database schema if it doesn't exist."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Workspaces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_hash TEXT UNIQUE NOT NULL,
                folder_uri TEXT,
                resolved_path TEXT,
                first_seen_at TEXT,
                last_seen_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Chats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cursor_composer_id TEXT UNIQUE NOT NULL,
                workspace_id INTEGER,
                title TEXT,
                mode TEXT,
                created_at TEXT,
                last_updated_at TEXT,
                source TEXT DEFAULT 'cursor',
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                text TEXT,
                rich_text TEXT,
                created_at TEXT,
                cursor_bubble_id TEXT,
                raw_json TEXT,
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            )
        """)
        
        # Chat files (relevant files per chat)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_files (
                chat_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                PRIMARY KEY (chat_id, path),
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            )
        """)
        
        # Tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                chat_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (chat_id, tag),
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            )
        """)
        
        # FTS5 virtual table for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS message_fts USING fts5(
                chat_id,
                text,
                rich_text,
                content='messages',
                content_rowid='id'
            )
        """)
        
        # Triggers to keep FTS5 in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                INSERT INTO message_fts(chat_id, text, rich_text, rowid)
                VALUES (new.chat_id, new.text, new.rich_text, new.id);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
                INSERT INTO message_fts(message_fts, rowid, chat_id, text, rich_text)
                VALUES('delete', old.id, old.chat_id, old.text, old.rich_text);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
                INSERT INTO message_fts(message_fts, rowid, chat_id, text, rich_text)
                VALUES('delete', old.id, old.chat_id, old.text, old.rich_text);
                INSERT INTO message_fts(chat_id, text, rich_text, rowid)
                VALUES (new.chat_id, new.text, new.rich_text, new.id);
            END
        """)
        
        # Indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chats_composer_id ON chats(cursor_composer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chats_workspace ON chats(workspace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chats_created ON chats(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workspaces_hash ON workspaces(workspace_hash)")
        
        self.conn.commit()
        logger.info("Database schema initialized at %s", self.db_path)
    
    def upsert_workspace(self, workspace: Workspace) -> int:
        """
        Insert or update a workspace.
        
        Parameters
        ----
        workspace : Workspace
            Workspace to upsert
            
        Returns
        ----
        int
            Workspace ID
        """
        cursor = self.conn.cursor()
        
        # Check if exists
        cursor.execute("SELECT id FROM workspaces WHERE workspace_hash = ?", (workspace.workspace_hash,))
        row = cursor.fetchone()
        
        if row:
            workspace_id = row[0]
            # Update
            cursor.execute("""
                UPDATE workspaces 
                SET folder_uri = ?, resolved_path = ?, last_seen_at = ?
                WHERE id = ?
            """, (
                workspace.folder_uri,
                workspace.resolved_path,
                datetime.now().isoformat() if workspace.last_seen_at else None,
                workspace_id
            ))
        else:
            # Insert
            cursor.execute("""
                INSERT INTO workspaces (workspace_hash, folder_uri, resolved_path, first_seen_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                workspace.workspace_hash,
                workspace.folder_uri,
                workspace.resolved_path,
                workspace.first_seen_at.isoformat() if workspace.first_seen_at else datetime.now().isoformat(),
                workspace.last_seen_at.isoformat() if workspace.last_seen_at else datetime.now().isoformat(),
            ))
            workspace_id = cursor.lastrowid
        
        self.conn.commit()
        return workspace_id
    
    def upsert_chat(self, chat: Chat) -> int:
        """
        Insert or update a chat and its messages.
        
        Parameters
        ----
        chat : Chat
            Chat to upsert
            
        Returns
        ----
        int
            Chat ID
        """
        cursor = self.conn.cursor()
        
        # Check if exists
        cursor.execute("SELECT id FROM chats WHERE cursor_composer_id = ?", (chat.cursor_composer_id,))
        row = cursor.fetchone()
        
        if row:
            chat_id = row[0]
            # Update chat metadata
            cursor.execute("""
                UPDATE chats 
                SET workspace_id = ?, title = ?, mode = ?, created_at = ?, last_updated_at = ?, source = ?
                WHERE id = ?
            """, (
                chat.workspace_id,
                chat.title or "",
                chat.mode.value,
                chat.created_at.isoformat() if chat.created_at else None,
                chat.last_updated_at.isoformat() if chat.last_updated_at else None,
                chat.source,
                chat_id
            ))
            # Delete old messages
            cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
            cursor.execute("DELETE FROM chat_files WHERE chat_id = ?", (chat_id,))
        else:
            # Insert
            cursor.execute("""
                INSERT INTO chats (cursor_composer_id, workspace_id, title, mode, created_at, last_updated_at, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                chat.cursor_composer_id,
                chat.workspace_id,
                chat.title or "",
                chat.mode.value,
                chat.created_at.isoformat() if chat.created_at else None,
                chat.last_updated_at.isoformat() if chat.last_updated_at else None,
                chat.source,
            ))
            chat_id = cursor.lastrowid
        
        # Insert messages
        for msg in chat.messages:
            cursor.execute("""
                INSERT INTO messages (chat_id, role, text, rich_text, created_at, cursor_bubble_id, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                chat_id,
                msg.role.value,
                msg.text or "",
                msg.rich_text or "",
                msg.created_at.isoformat() if msg.created_at else None,
                msg.cursor_bubble_id,
                json.dumps(msg.raw_json) if msg.raw_json else None,
            ))
        
        # Insert relevant files
        for file_path in chat.relevant_files:
            cursor.execute("""
                INSERT OR IGNORE INTO chat_files (chat_id, path)
                VALUES (?, ?)
            """, (chat_id, file_path))
        
        self.conn.commit()
        return chat_id
    
    def search_chats(self, query: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search chats using full-text search.
        
        Parameters
        ----
        query : str
            Search query
        limit : int
            Maximum number of results
        offset : int
            Offset for pagination
            
        Returns
        ----
        List[Dict[str, Any]]
            List of matching chats with metadata
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT c.id, c.cursor_composer_id, c.title, c.mode, c.created_at, c.source,
                   w.workspace_hash, w.resolved_path
            FROM chats c
            LEFT JOIN workspaces w ON c.workspace_id = w.id
            INNER JOIN message_fts fts ON c.id = fts.chat_id
            WHERE message_fts MATCH ?
            ORDER BY c.created_at DESC
            LIMIT ? OFFSET ?
        """, (query, limit, offset))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "composer_id": row[1],
                "title": row[2],
                "mode": row[3],
                "created_at": row[4],
                "source": row[5],
                "workspace_hash": row[6],
                "workspace_path": row[7],
            })
        
        return results
    
    def get_chat(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a chat with all its messages.
        
        Parameters
        ----
        chat_id : int
            Chat ID
            
        Returns
        ----
        Dict[str, Any]
            Chat data with messages, or None if not found
        """
        cursor = self.conn.cursor()
        
        # Get chat
        cursor.execute("""
            SELECT c.*, w.workspace_hash, w.resolved_path
            FROM chats c
            LEFT JOIN workspaces w ON c.workspace_id = w.id
            WHERE c.id = ?
        """, (chat_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        chat_data = {
            "id": row[0],
            "composer_id": row[1],
            "workspace_id": row[2],
            "title": row[3],
            "mode": row[4],
            "created_at": row[5],
            "last_updated_at": row[6],
            "source": row[7],
            "workspace_hash": row[8],
            "workspace_path": row[9],
            "messages": [],
            "files": [],
        }
        
        # Get messages
        cursor.execute("""
            SELECT role, text, rich_text, created_at, cursor_bubble_id
            FROM messages
            WHERE chat_id = ?
            ORDER BY created_at ASC
        """, (chat_id,))
        
        for msg_row in cursor.fetchall():
            chat_data["messages"].append({
                "role": msg_row[0],
                "text": msg_row[1],
                "rich_text": msg_row[2],
                "created_at": msg_row[3],
                "bubble_id": msg_row[4],
            })
        
        # Get files
        cursor.execute("SELECT path FROM chat_files WHERE chat_id = ?", (chat_id,))
        chat_data["files"] = [row[0] for row in cursor.fetchall()]
        
        return chat_data
    
    def count_chats(self, workspace_id: Optional[int] = None) -> int:
        """
        Count total chats, optionally filtered by workspace.
        
        Parameters
        ----
        workspace_id : int, optional
            Filter by workspace
            
        Returns
        ----
        int
            Total count of chats
        """
        cursor = self.conn.cursor()
        
        if workspace_id:
            cursor.execute("SELECT COUNT(*) FROM chats WHERE workspace_id = ?", (workspace_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM chats")
        
        return cursor.fetchone()[0]
    
    def count_search(self, query: str) -> int:
        """
        Count search results for a query.
        
        Parameters
        ----
        query : str
            Search query (FTS5 syntax)
            
        Returns
        ----
        int
            Total count of matching chats
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(DISTINCT c.id)
            FROM chats c
            INNER JOIN message_fts fts ON c.id = fts.chat_id
            WHERE message_fts MATCH ?
        """, (query,))
        
        return cursor.fetchone()[0]
    
    def list_chats(self, workspace_id: Optional[int] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List chats with optional filtering.
        
        Parameters
        ----
        workspace_id : int, optional
            Filter by workspace
        limit : int
            Maximum number of results
        offset : int
            Offset for pagination
            
        Returns
        ----
        List[Dict[str, Any]]
            List of chats
        """
        cursor = self.conn.cursor()
        
        if workspace_id:
            cursor.execute("""
                SELECT c.id, c.cursor_composer_id, c.title, c.mode, c.created_at, c.source,
                       w.workspace_hash, w.resolved_path
                FROM chats c
                LEFT JOIN workspaces w ON c.workspace_id = w.id
                WHERE c.workspace_id = ?
                ORDER BY c.created_at DESC
                LIMIT ? OFFSET ?
            """, (workspace_id, limit, offset))
        else:
            cursor.execute("""
                SELECT c.id, c.cursor_composer_id, c.title, c.mode, c.created_at, c.source,
                       w.workspace_hash, w.resolved_path
                FROM chats c
                LEFT JOIN workspaces w ON c.workspace_id = w.id
                ORDER BY c.created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "composer_id": row[1],
                "title": row[2],
                "mode": row[3],
                "created_at": row[4],
                "source": row[5],
                "workspace_hash": row[6],
                "workspace_path": row[7],
            })
        
        return results
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

