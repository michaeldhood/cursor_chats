# Database Exploration Scripts

Utility scripts for exploring and exporting data from Cursor's databases and our aggregated database.

## Scripts

### `find_chats.py`

Find chats in the aggregated database by various criteria.

```bash
# Find by title
python scripts/database/find_chats.py --title "PR10 understanding"

# Find by composer ID
python scripts/database/find_chats.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab

# Find empty chats
python scripts/database/find_chats.py --empty

# Limit results
python scripts/database/find_chats.py --limit 20
```

### `export_chat.py`

Export a chat from the aggregated database to JSON (includes messages, files, tags).

```bash
# Export by chat ID
python scripts/database/export_chat.py 4425 --output examples/chat_4425.json

# Export by composer ID
python scripts/database/export_chat.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab
```

### `search_workspaces.py`

Search across all Cursor workspace databases for a composer ID or pattern.

```bash
# Search for composer ID
python scripts/database/search_workspaces.py fbd30712-94fd-48d3-b674-ed162dbf56ab

# Search for key patterns
python scripts/database/search_workspaces.py --pattern "composer.composerData"
```

### `query_global_storage.py`

Query Cursor's global storage (`cursorDiskKV` table).

```bash
# Get composer data
python scripts/database/query_global_storage.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab

# Get any key
python scripts/database/query_global_storage.py --key "composerData:fbd30712-94fd-48d3-b674-ed162dbf56ab"

# Discover keys matching pattern
python scripts/database/query_global_storage.py --discover --pattern "composerData" --limit 10
```

### `fetch_bubble.py`

Fetch individual bubble content from Cursor's global storage.

```bash
# Fetch single bubble
python scripts/database/fetch_bubble.py fbd30712-94fd-48d3-b674-ed162dbf56ab d0216c2d-48f9-4f0b-bf06-d40f09fdf80c

# With output file
python scripts/database/fetch_bubble.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab --bubble-id d0216c2d-48f9-4f0b-bf06-d40f09fdf80c --output bubble.json

# Fetch multiple bubbles
python scripts/database/fetch_bubble.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab --batch bubble1 bubble2 bubble3 --output-dir bubbles/
```

### `discover_keys.py`

Discover what keys exist in Cursor databases (useful for reverse-engineering).

```bash
# Discover in global storage
python scripts/database/discover_keys.py --global --pattern "composer"

# Discover in workspace storage
python scripts/database/discover_keys.py --workspace --pattern "composer.composerData"

# Sort by size (find largest values)
python scripts/database/discover_keys.py --global --pattern "bubbleId" --by-size
```

## Common Patterns

### Finding Empty Chats

```bash
# In aggregated DB
python scripts/database/find_chats.py --empty

# Export one for inspection
python scripts/database/export_chat.py 4425 --output examples/empty_chat.json
```

### Tracing a Composer ID

```bash
# 1. Find in aggregated DB
python scripts/database/find_chats.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab

# 2. Check if it exists in workspace storage
python scripts/database/search_workspaces.py fbd30712-94fd-48d3-b674-ed162dbf56ab

# 3. Get raw source data from global storage
python scripts/database/query_global_storage.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab --output raw_source.json
```

### Exporting Full Chat with Bubbles

```bash
# 1. Get composer data to see bubble IDs
python scripts/database/query_global_storage.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab --output composer.json

# 2. Extract bubble IDs from composer.json, then fetch them
python scripts/database/fetch_bubble.py --composer-id fbd30712-94fd-48d3-b674-ed162dbf56ab --batch bubble1 bubble2 bubble3 --output-dir bubbles/
```

## Notes

- All scripts use the project's config functions (`get_default_db_path()`, etc.) for OS-specific paths
- Scripts handle both `bytes` and `str` blob encoding automatically
- JSON output uses `default=str` to handle datetime objects
- Workspace search can be slow if you have many workspaces

