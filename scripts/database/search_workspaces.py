#!/usr/bin/env python3
"""
Search across all Cursor workspace databases for a composer ID or other patterns.

Searches in workspaceStorage/*/state.vscdb ItemTable for any references.

Usage:
    python scripts/database/search_workspaces.py fbd30712-94fd-48d3-b674-ed162dbf56ab
    python scripts/database/search_workspaces.py --pattern "composer.composerData"
"""
import sqlite3
import json
import argparse
from pathlib import Path
from src.core.config import get_cursor_workspace_storage_path


def search_workspaces(search_term, pattern_mode=False):
    """
    Search all workspace databases for a term.
    
    Parameters
    ----
    search_term : str
        Composer ID or pattern to search for
    pattern_mode : bool
        If True, search in keys; if False, search in values
    """
    workspace_storage = get_cursor_workspace_storage_path()
    
    if not workspace_storage.exists():
        print(f"Workspace storage not found: {workspace_storage}")
        return
    
    found_in = []
    
    for ws_dir in workspace_storage.iterdir():
        if not ws_dir.is_dir():
            continue
        
        db_path = ws_dir / "state.vscdb"
        if not db_path.exists():
            continue
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            if pattern_mode:
                # Search in keys
                cursor.execute("SELECT key, value FROM ItemTable WHERE key LIKE ?", (f'%{search_term}%',))
            else:
                # Search in values (slower, but finds composer IDs in JSON)
                cursor.execute("SELECT key, value FROM ItemTable WHERE value LIKE ?", (f'%{search_term}%',))
            
            rows = cursor.fetchall()
            if rows:
                found_in.append((ws_dir.name, rows))
            
            conn.close()
        except Exception as e:
            print(f"Error reading {ws_dir.name}: {e}")
            continue
    
    if found_in:
        print(f"Found '{search_term}' in {len(found_in)} workspace(s):\n")
        for ws_name, rows in found_in:
            print(f"=== Workspace: {ws_name} ===")
            for key, value in rows[:5]:  # Limit to first 5 matches per workspace
                print(f"  Key: {key}")
                try:
                    if isinstance(value, bytes):
                        data = json.loads(value.decode('utf-8'))
                    else:
                        data = json.loads(value)
                    
                    if isinstance(data, dict):
                        print(f"    Keys: {list(data.keys())[:10]}")
                        if 'tabs' in data:
                            for tab in data.get('tabs', [])[:2]:
                                if search_term in str(tab.get('composerId', '')):
                                    print(f"    Found as TAB - bubbles: {len(tab.get('bubbles', []))}")
                    elif isinstance(data, list):
                        print(f"    List with {len(data)} items")
                except:
                    print(f"    Raw (first 200): {str(value)[:200]}")
            if len(rows) > 5:
                print(f"    ... and {len(rows) - 5} more matches")
            print()
    else:
        print(f"'{search_term}' NOT FOUND in any workspace storage")


def main():
    parser = argparse.ArgumentParser(description="Search Cursor workspace databases")
    parser.add_argument("search_term", help="Composer ID or pattern to search for")
    parser.add_argument("--pattern", action="store_true", help="Search in keys instead of values")
    
    args = parser.parse_args()
    search_workspaces(args.search_term, pattern_mode=args.pattern)


if __name__ == "__main__":
    main()

