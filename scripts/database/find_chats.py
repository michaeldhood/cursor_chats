#!/usr/bin/env python3
"""
Find chats in the aggregated database by title, composer ID, or other criteria.

Usage:
    python scripts/database/find_chats.py --title "PR10 understanding"
    python scripts/database/find_chats.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab
    python scripts/database/find_chats.py --empty  # Find empty chats
    python scripts/database/find_chats.py --limit 20
"""
import sqlite3
import argparse
from pathlib import Path
from src.core.config import get_default_db_path


def find_chats(title=None, composer_id=None, empty_only=False, limit=10):
    """
    Find chats matching criteria.
    
    Parameters
    ----
    title : str, optional
        Filter by title (exact match)
    composer_id : str, optional
        Filter by composer ID
    empty_only : bool
        Only show chats with 0 messages
    limit : int
        Maximum results to return
    """
    db_path = get_default_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if title:
        conditions.append("c.title = ?")
        params.append(title)
    
    if composer_id:
        conditions.append("c.cursor_composer_id = ?")
        params.append(composer_id)
    
    if empty_only:
        conditions.append("c.messages_count = 0")
    
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    
    query = f"""
        SELECT c.id, c.cursor_composer_id, c.title, c.mode, c.created_at, 
               c.source, c.messages_count, c.last_updated_at,
               w.workspace_hash, w.resolved_path
        FROM chats c
        LEFT JOIN workspaces w ON c.workspace_id = w.id
        {where_clause}
        ORDER BY c.created_at DESC
        LIMIT ?
    """
    
    params.append(limit)
    cursor.execute(query, params)
    
    print(f"\nFound chats (showing up to {limit}):")
    print("-" * 100)
    print(f"{'ID':<6} {'Title':<30} {'Mode':<8} {'Msgs':<6} {'Created':<20} {'Workspace':<20}")
    print("-" * 100)
    
    for row in cursor.fetchall():
        title_display = (row['title'] or 'Untitled')[:28]
        workspace_display = (row['workspace_hash'] or '-')[:18]
        created = row['created_at'][:19] if row['created_at'] else '-'
        
        print(f"{row['id']:<6} {title_display:<30} {row['mode']:<8} "
              f"{row['messages_count']:<6} {created:<20} {workspace_display:<20}")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Find chats in aggregated database")
    parser.add_argument("--title", help="Filter by exact title match")
    parser.add_argument("--composer-id", help="Filter by composer UUID")
    parser.add_argument("--empty", action="store_true", help="Only show empty chats (0 messages)")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results (default: 10)")
    
    args = parser.parse_args()
    find_chats(
        title=args.title,
        composer_id=args.composer_id,
        empty_only=args.empty,
        limit=args.limit
    )


if __name__ == "__main__":
    main()

