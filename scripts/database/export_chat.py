#!/usr/bin/env python3
"""
Export a chat from the aggregated database to JSON.

Includes all messages, files, tags, and metadata.

Usage:
    python scripts/database/export_chat.py 4425 --output examples/chat_4425.json
    python scripts/database/export_chat.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab
"""
import sqlite3
import json
import argparse
from pathlib import Path
from src.core.config import get_default_db_path


def export_chat(chat_id=None, composer_id=None, output_path=None):
    """
    Export a chat to JSON.
    
    Parameters
    ----
    chat_id : int, optional
        Chat ID in aggregated database
    composer_id : str, optional
        Composer UUID (alternative to chat_id)
    output_path : str, optional
        Output file path (defaults to chat_data_{id}.json)
    """
    db_path = get_default_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    cursor = conn.cursor()
    
    # Resolve chat_id if composer_id provided
    if composer_id and not chat_id:
        cursor.execute("SELECT id FROM chats WHERE cursor_composer_id = ?", (composer_id,))
        row = cursor.fetchone()
        if not row:
            print(f"Chat not found for composer_id: {composer_id}")
            conn.close()
            return
        chat_id = row[0]
    
    if not chat_id:
        print("Error: Must provide either --chat-id or --composer-id")
        conn.close()
        return
    
    # Get chat metadata with workspace join
    cursor.execute("""
        SELECT c.*, w.workspace_hash, w.folder_uri, w.resolved_path
        FROM chats c
        LEFT JOIN workspaces w ON c.workspace_id = w.id
        WHERE c.id = ?
    """, (chat_id,))
    
    chat_row = cursor.fetchone()
    if not chat_row:
        print(f"Chat ID {chat_id} not found")
        conn.close()
        return
    
    chat_data = dict(chat_row)
    
    # Get all messages with raw_json
    cursor.execute("""
        SELECT id, chat_id, role, text, rich_text, created_at, 
               cursor_bubble_id, raw_json, message_type
        FROM messages
        WHERE chat_id = ?
        ORDER BY created_at ASC
    """, (chat_id,))
    
    messages = []
    for row in cursor.fetchall():
        msg = dict(row)
        # Parse raw_json if present
        if msg['raw_json']:
            try:
                msg['raw_json'] = json.loads(msg['raw_json'])
            except:
                pass  # Keep as string if parse fails
        messages.append(msg)
    
    chat_data['messages'] = messages
    
    # Get files
    cursor.execute("SELECT path FROM chat_files WHERE chat_id = ?", (chat_id,))
    chat_data['files'] = [row[0] for row in cursor.fetchall()]
    
    # Get tags
    cursor.execute("SELECT tag FROM tags WHERE chat_id = ? ORDER BY tag", (chat_id,))
    chat_data['tags'] = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    # Determine output path
    if not output_path:
        output_path = f"chat_data_{chat_id}.json"
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write JSON
    with open(output_file, "w") as f:
        json.dump(chat_data, f, indent=2, default=str)
    
    print(f"Exported chat ID {chat_id} ({len(messages)} messages)")
    print(f"  Title: {chat_data.get('title', 'Untitled')}")
    print(f"  Output: {output_file.absolute()}")


def main():
    parser = argparse.ArgumentParser(description="Export chat from aggregated database to JSON")
    parser.add_argument("chat_id", type=int, nargs="?", help="Chat ID in database")
    parser.add_argument("--composer-id", help="Composer UUID (alternative to chat_id)")
    parser.add_argument("--output", "-o", help="Output file path")
    
    args = parser.parse_args()
    export_chat(
        chat_id=args.chat_id,
        composer_id=args.composer_id,
        output_path=args.output
    )


if __name__ == "__main__":
    main()

