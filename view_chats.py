#!/usr/bin/env python3
"""
A simple script to list and view Cursor chat files in the current directory and common output directories.
"""

import os
import re
import sys

def list_chat_files(directories=['.', 'chat_exports', 'markdown_chats']):
    """List all chat files in the specified directories."""
    all_files = []
    
    # Collect files from all specified directories
    for directory in directories:
        if os.path.exists(directory):
            for f in os.listdir(directory):
                if f.endswith('.md') and f.startswith('chat_'):
                    all_files.append(os.path.join(directory, f))
    
    if not all_files:
        print("No chat files found in the specified directories.")
        return
    
    # Group files by hash
    chat_groups = {}
    for file in all_files:
        match = re.match(r'.*chat_([a-f0-9]+)(?:_([a-f0-9-]+))?.md', file)
        if match:
            hash_val = match.group(1)
            if hash_val not in chat_groups:
                chat_groups[hash_val] = []
            chat_groups[hash_val].append(file)
    
    # Print chat groups
    for i, (hash_val, group_files) in enumerate(chat_groups.items()):
        print(f"{i+1}. Group {hash_val[:8]}... ({len(group_files)} files)")
        
        # Identify parent files
        parent_files = [f for f in group_files if re.match(r'.*chat_[a-f0-9]+\.md$', f)]
        other_files = [f for f in group_files if f not in parent_files]
        
        # Print parent files first
        for parent_file in parent_files:
            print(f"   - {parent_file} (Parent)")
        
        # Then print child files
        for j, file in enumerate(sorted(other_files)):
            print(f"   {j+1}. {file}")
        print()

def view_chat_file(filepath):
    """View the contents of a chat file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"\n{'='*80}\n{filepath}\n{'='*80}\n")
            print(content)
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")

def main():
    if len(sys.argv) == 1:
        list_chat_files()
        print("\nTo view a chat file, run: python view_chats.py FILENAME")
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
        # Check if it's a direct file or a partial filename
        if os.path.isfile(filename):
            view_chat_file(filename)
        else:
            # Try to find the file in common directories
            found = False
            for directory in ['.', 'chat_exports', 'markdown_chats']:
                potential_path = os.path.join(directory, filename)
                if os.path.isfile(potential_path):
                    view_chat_file(potential_path)
                    found = True
                    break
            
            if not found:
                print(f"File not found: {filename}")
                list_chat_files()
    else:
        print("Usage: python view_chats.py [FILENAME]")

if __name__ == "__main__":
    main() 