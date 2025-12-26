#!/usr/bin/env python3
"""
Fetch individual bubble content from Cursor's global storage.

Bubbles are stored at key: bubbleId:{composerId}:{bubbleId}

Usage:
    python scripts/database/fetch_bubble.py fbd30712-94fd-48d3-b674-ed162dbf56ab d0216c2d-48f9-4f0b-bf06-d40f09fdf80c
    python scripts/database/fetch_bubble.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab --bubble-id d0216c2d-48f9-4f0b-bf06-d40f09fdf80c --output bubble.json
"""
import sqlite3
import json
import argparse
from pathlib import Path
from src.core.config import get_cursor_global_storage_path


def fetch_bubble(composer_id, bubble_id, output_path=None):
    """
    Fetch a single bubble's content.
    
    Parameters
    ----
    composer_id : str
        Composer UUID
    bubble_id : str
        Bubble UUID
    output_path : str, optional
        Save to JSON file
    """
    global_db = get_cursor_global_storage_path() / "state.vscdb"
    
    if not global_db.exists():
        print(f"Global database not found: {global_db}")
        return None
    
    conn = sqlite3.connect(str(global_db))
    cursor = conn.cursor()
    
    key = f"bubbleId:{composer_id}:{bubble_id}"
    cursor.execute("SELECT value FROM cursorDiskKV WHERE key = ?", (key,))
    row = cursor.fetchone()
    
    if not row:
        print(f"Bubble not found: {key}")
        conn.close()
        return None
    
    value = row[0]
    if isinstance(value, bytes):
        bubble_data = json.loads(value.decode('utf-8'))
    else:
        bubble_data = json.loads(value)
    
    conn.close()
    
    # Print summary
    print(f"Bubble: {bubble_id}")
    print(f"Type: {bubble_data.get('type')} ({'user' if bubble_data.get('type') == 1 else 'assistant'})")
    print(f"Text length: {len(bubble_data.get('text', ''))}")
    
    if bubble_data.get('thinking'):
        thinking_text = bubble_data['thinking'].get('text', '')
        print(f"Thinking: {len(thinking_text)} chars")
    
    if bubble_data.get('codeBlocks'):
        print(f"Code blocks: {len(bubble_data['codeBlocks'])}")
    
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(bubble_data, f, indent=2, default=str)
        print(f"\nSaved to: {output_file.absolute()}")
    else:
        print("\nFull bubble data:")
        print(json.dumps(bubble_data, indent=2, default=str))
    
    return bubble_data


def fetch_bubbles_batch(composer_id, bubble_ids, output_dir=None):
    """
    Fetch multiple bubbles in a single query.
    
    Parameters
    ----
    composer_id : str
        Composer UUID
    bubble_ids : list[str]
        List of bubble UUIDs
    output_dir : str, optional
        Directory to save individual bubble files
    """
    global_db = get_cursor_global_storage_path() / "state.vscdb"
    
    if not global_db.exists():
        print(f"Global database not found: {global_db}")
        return {}
    
    conn = sqlite3.connect(str(global_db))
    cursor = conn.cursor()
    
    # Build keys and query with IN clause
    keys = [f"bubbleId:{composer_id}:{bubble_id}" for bubble_id in bubble_ids]
    placeholders = ','.join('?' * len(keys))
    
    cursor.execute(
        f"SELECT key, value FROM cursorDiskKV WHERE key IN ({placeholders})",
        keys
    )
    
    bubbles = {}
    for row in cursor.fetchall():
        key_str = row[0]
        value_data = row[1]
        
        if value_data is None:
            continue
        
        # Extract bubble_id from key
        parts = key_str.split(':', 2)
        if len(parts) == 3 and parts[0] == "bubbleId":
            bubble_id = parts[2]
            try:
                if isinstance(value_data, bytes):
                    bubble_data = json.loads(value_data.decode('utf-8'))
                else:
                    bubble_data = json.loads(value_data)
                bubbles[bubble_id] = bubble_data
                
                if output_dir:
                    output_file = Path(output_dir) / f"bubble_{bubble_id}.json"
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_file, "w") as f:
                        json.dump(bubble_data, f, indent=2, default=str)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Failed to parse bubble {bubble_id}: {e}")
    
    conn.close()
    
    print(f"Fetched {len(bubbles)} bubbles")
    if output_dir:
        print(f"Saved to: {Path(output_dir).absolute()}")
    
    return bubbles


def main():
    parser = argparse.ArgumentParser(description="Fetch bubble content from Cursor global storage")
    parser.add_argument("composer_id", nargs="?", help="Composer UUID")
    parser.add_argument("bubble_id", nargs="?", help="Bubble UUID")
    parser.add_argument("--composer-id", dest="composer_id_arg", help="Composer UUID (alternative)")
    parser.add_argument("--bubble-id", dest="bubble_id_arg", help="Bubble UUID (alternative)")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--batch", nargs="+", help="Fetch multiple bubbles (provide bubble IDs)")
    parser.add_argument("--output-dir", help="Directory for batch output")
    
    args = parser.parse_args()
    
    composer_id = args.composer_id or args.composer_id_arg
    bubble_id = args.bubble_id or args.bubble_id_arg
    
    if args.batch and composer_id:
        fetch_bubbles_batch(composer_id, args.batch, args.output_dir)
    elif composer_id and bubble_id:
        fetch_bubble(composer_id, bubble_id, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

