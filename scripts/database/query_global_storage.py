#!/usr/bin/env python3
"""
Query Cursor's global storage cursorDiskKV table.

Can fetch composerData, bubble data, or discover key patterns.

Usage:
    python scripts/database/query_global_storage.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab
    python scripts/database/query_global_storage.py --key "composerData:fbd30712-94fd-48d3-b674-ed162dbf56ab"
    python scripts/database/query_global_storage.py --discover --pattern "composerData"
    python scripts/database/query_global_storage.py --discover --pattern "bubbleId" --limit 5
"""
import sqlite3
import json
import argparse
from pathlib import Path
from src.core.config import get_cursor_global_storage_path


def get_composer_data(composer_id, output_path=None):
    """
    Get composerData for a specific composer ID.
    
    Parameters
    ----
    composer_id : str
        Composer UUID
    output_path : str, optional
        Save to JSON file
    """
    global_db = get_cursor_global_storage_path() / "state.vscdb"
    
    if not global_db.exists():
        print(f"Global database not found: {global_db}")
        return None
    
    conn = sqlite3.connect(str(global_db))
    cursor = conn.cursor()
    
    key = f"composerData:{composer_id}"
    cursor.execute("SELECT value FROM cursorDiskKV WHERE key = ?", (key,))
    row = cursor.fetchone()
    
    if not row:
        print(f"Composer not found: {composer_id}")
        conn.close()
        return None
    
    value = row[0]
    if isinstance(value, bytes):
        data = json.loads(value.decode('utf-8'))
    else:
        data = json.loads(value)
    
    conn.close()
    
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Saved to: {output_file.absolute()}")
    else:
        print(json.dumps(data, indent=2, default=str))
    
    return data


def get_key(key, output_path=None):
    """
    Get any key from cursorDiskKV.
    
    Parameters
    ----
    key : str
        Exact key to fetch
    output_path : str, optional
        Save to JSON file
    """
    global_db = get_cursor_global_storage_path() / "state.vscdb"
    
    if not global_db.exists():
        print(f"Global database not found: {global_db}")
        return None
    
    conn = sqlite3.connect(str(global_db))
    cursor = conn.cursor()
    
    cursor.execute("SELECT value FROM cursorDiskKV WHERE key = ?", (key,))
    row = cursor.fetchone()
    
    if not row:
        print(f"Key not found: {key}")
        conn.close()
        return None
    
    value = row[0]
    if isinstance(value, bytes):
        data = json.loads(value.decode('utf-8'))
    else:
        data = json.loads(value)
    
    conn.close()
    
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Saved to: {output_file.absolute()}")
    else:
        print(json.dumps(data, indent=2, default=str))
    
    return data


def discover_keys(pattern, limit=20):
    """
    Find keys matching a pattern, sorted by size.
    
    Parameters
    ----
    pattern : str
        Pattern to match (SQL LIKE)
    limit : int
        Maximum results
    """
    global_db = get_cursor_global_storage_path() / "state.vscdb"
    
    if not global_db.exists():
        print(f"Global database not found: {global_db}")
        return
    
    conn = sqlite3.connect(str(global_db))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT key, length(value) as size
        FROM cursorDiskKV 
        WHERE key LIKE ?
        ORDER BY size DESC
        LIMIT ?
    """, (f'%{pattern}%', limit))
    
    print(f"\nKeys matching '{pattern}' (sorted by size):")
    print("-" * 80)
    print(f"{'Key':<60} {'Size (bytes)':<15}")
    print("-" * 80)
    
    for row in cursor.fetchall():
        print(f"{row[0]:<60} {row[1]:<15}")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Query Cursor global storage")
    parser.add_argument("--composer-id", help="Composer UUID to fetch")
    parser.add_argument("--key", help="Exact key to fetch")
    parser.add_argument("--discover", action="store_true", help="Discover keys matching pattern")
    parser.add_argument("--pattern", help="Pattern for discovery (SQL LIKE)")
    parser.add_argument("--limit", type=int, default=20, help="Limit for discovery (default: 20)")
    parser.add_argument("--output", "-o", help="Save output to JSON file")
    
    args = parser.parse_args()
    
    if args.composer_id:
        get_composer_data(args.composer_id, args.output)
    elif args.key:
        get_key(args.key, args.output)
    elif args.discover and args.pattern:
        discover_keys(args.pattern, args.limit)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

