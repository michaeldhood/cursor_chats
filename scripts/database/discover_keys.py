#!/usr/bin/env python3
"""
Discover key patterns in Cursor databases (workspace or global).

Helps reverse-engineer what keys exist and what they contain.

Usage:
    python scripts/database/discover_keys.py --global --pattern "composer"
    python scripts/database/discover_keys.py --workspace --pattern "composer.composerData"
    python scripts/database/discover_keys.py --global --pattern "bubbleId" --by-size
"""
import sqlite3
import argparse
from pathlib import Path
from src.core.config import get_cursor_workspace_storage_path, get_cursor_global_storage_path


def discover_global_keys(pattern=None, by_size=False, limit=50):
    """
    Discover keys in global storage cursorDiskKV.
    
    Parameters
    ----
    pattern : str, optional
        Pattern to match (SQL LIKE)
    by_size : bool
        Sort by value size (largest first)
    limit : int
        Maximum results
    """
    global_db = get_cursor_global_storage_path() / "state.vscdb"
    
    if not global_db.exists():
        print(f"Global database not found: {global_db}")
        return
    
    conn = sqlite3.connect(str(global_db))
    cursor = conn.cursor()
    
    if pattern:
        if by_size:
            query = """
                SELECT key, length(value) as size
                FROM cursorDiskKV 
                WHERE key LIKE ?
                ORDER BY size DESC
                LIMIT ?
            """
        else:
            query = """
                SELECT key, length(value) as size
                FROM cursorDiskKV 
                WHERE key LIKE ?
                ORDER BY key
                LIMIT ?
            """
        cursor.execute(query, (f'%{pattern}%', limit))
    else:
        if by_size:
            query = """
                SELECT key, length(value) as size
                FROM cursorDiskKV 
                ORDER BY size DESC
                LIMIT ?
            """
        else:
            query = """
                SELECT key, length(value) as size
                FROM cursorDiskKV 
                ORDER BY key
                LIMIT ?
            """
        cursor.execute(query, (limit,))
    
    print(f"\nKeys in global storage{' (matching pattern)' if pattern else ''}:")
    print("-" * 100)
    print(f"{'Key':<70} {'Size (bytes)':<15}")
    print("-" * 100)
    
    for row in cursor.fetchall():
        print(f"{row[0]:<70} {row[1]:<15}")
    
    conn.close()


def discover_workspace_keys(pattern=None, by_size=False, limit=50, workspace_hash=None):
    """
    Discover keys in workspace storage ItemTable.
    
    Parameters
    ----
    pattern : str, optional
        Pattern to match (SQL LIKE)
    by_size : bool
        Sort by value size
    limit : int
        Maximum results per workspace
    workspace_hash : str, optional
        Specific workspace to search (otherwise searches all)
    """
    workspace_storage = get_cursor_workspace_storage_path()
    
    if not workspace_storage.exists():
        print(f"Workspace storage not found: {workspace_storage}")
        return
    
    workspaces = []
    if workspace_hash:
        ws_dir = workspace_storage / workspace_hash
        if ws_dir.exists():
            workspaces = [ws_dir]
    else:
        workspaces = [d for d in workspace_storage.iterdir() if d.is_dir()]
    
    for ws_dir in workspaces:
        db_path = ws_dir / "state.vscdb"
        if not db_path.exists():
            continue
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            if pattern:
                if by_size:
                    query = """
                        SELECT key, length(value) as size
                        FROM ItemTable 
                        WHERE key LIKE ?
                        ORDER BY size DESC
                        LIMIT ?
                    """
                else:
                    query = """
                        SELECT key, length(value) as size
                        FROM ItemTable 
                        WHERE key LIKE ?
                        ORDER BY key
                        LIMIT ?
                    """
                cursor.execute(query, (f'%{pattern}%', limit))
            else:
                if by_size:
                    query = """
                        SELECT key, length(value) as size
                        FROM ItemTable 
                        ORDER BY size DESC
                        LIMIT ?
                    """
                else:
                    query = """
                        SELECT key, length(value) as size
                        FROM ItemTable 
                        ORDER BY key
                        LIMIT ?
                    """
                cursor.execute(query, (limit,))
            
            rows = cursor.fetchall()
            if rows:
                print(f"\n=== Workspace: {ws_dir.name} ===")
                print("-" * 100)
                print(f"{'Key':<70} {'Size (bytes)':<15}")
                print("-" * 100)
                for row in rows:
                    print(f"{row[0]:<70} {row[1]:<15}")
            
            conn.close()
        except Exception as e:
            print(f"Error reading {ws_dir.name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Discover keys in Cursor databases")
    parser.add_argument("--global", dest="use_global", action="store_true", help="Search global storage")
    parser.add_argument("--workspace", dest="use_workspace", action="store_true", help="Search workspace storage")
    parser.add_argument("--pattern", help="Pattern to match (SQL LIKE)")
    parser.add_argument("--by-size", action="store_true", help="Sort by value size (largest first)")
    parser.add_argument("--limit", type=int, default=50, help="Maximum results (default: 50)")
    parser.add_argument("--workspace-hash", help="Specific workspace hash to search")
    
    args = parser.parse_args()
    
    if args.use_global:
        discover_global_keys(args.pattern, args.by_size, args.limit)
    elif args.use_workspace:
        discover_workspace_keys(args.pattern, args.by_size, args.limit, args.workspace_hash)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

