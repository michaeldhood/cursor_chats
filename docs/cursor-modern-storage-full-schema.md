## Cursor Modern Storage: Full SQLite Schema Dump

This is a **schema + columns** dump for Cursor's modern chat storage SQLite DBs:

- Global: `globalStorage/state.vscdb`
- Workspace: `workspaceStorage/<hash>/state.vscdb`

Notes:
- Cursor may add/remove tables across versions; this doc reflects the DBs inspected on this machine.
- Some `sql` definitions in the sqlite_master table are truncated in the table view for readability.

---

## DB: `/Users/michaelhood/Library/Application Support/Cursor/User/globalStorage/state.vscdb`

### sqlite_master objects

| type | name | tbl_name | sql |
| --- | --- | --- | --- |
| index | `sqlite_autoindex_ItemTable_1` | `ItemTable` | `` |
| index | `sqlite_autoindex_cursorDiskKV_1` | `cursorDiskKV` | `` |
| table | `ItemTable` | `ItemTable` | `CREATE TABLE ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)` |
| table | `cursorDiskKV` | `cursorDiskKV` | `CREATE TABLE cursorDiskKV (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)` |

### Tables and columns

#### `ItemTable`

| cid | name | type | notnull | dflt_value | pk |
| --- | --- | --- | --- | --- | --- |
| 0 | `key` | `TEXT` | 0 | `None` | 0 |
| 1 | `value` | `BLOB` | 0 | `None` | 0 |

#### `cursorDiskKV`

| cid | name | type | notnull | dflt_value | pk |
| --- | --- | --- | --- | --- | --- |
| 0 | `key` | `TEXT` | 0 | `None` | 0 |
| 1 | `value` | `BLOB` | 0 | `None` | 0 |

### Foreign keys

(none)

---

## DB: `/Users/michaelhood/git/build/cursor_chats/workspaceStorage/10770782bbd95d5ae0035836c987047a/state.vscdb`

### sqlite_master objects

| type | name | tbl_name | sql |
| --- | --- | --- | --- |
| index | `sqlite_autoindex_ItemTable_1` | `ItemTable` | `` |
| index | `sqlite_autoindex_cursorDiskKV_1` | `cursorDiskKV` | `` |
| table | `ItemTable` | `ItemTable` | `CREATE TABLE ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)` |
| table | `cursorDiskKV` | `cursorDiskKV` | `CREATE TABLE cursorDiskKV (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)` |

### Tables and columns

#### `ItemTable`

| cid | name | type | notnull | dflt_value | pk |
| --- | --- | --- | --- | --- | --- |
| 0 | `key` | `TEXT` | 0 | `None` | 0 |
| 1 | `value` | `BLOB` | 0 | `None` | 0 |

#### `cursorDiskKV`

| cid | name | type | notnull | dflt_value | pk |
| --- | --- | --- | --- | --- | --- |
| 0 | `key` | `TEXT` | 0 | `None` | 0 |
| 1 | `value` | `BLOB` | 0 | `None` | 0 |

### Foreign keys

(none)

---

## DB: `/Users/michaelhood/git/build/cursor_chats/workspaceStorage/1742529077861/state.vscdb`

### sqlite_master objects

| type | name | tbl_name | sql |
| --- | --- | --- | --- |
| index | `sqlite_autoindex_ItemTable_1` | `ItemTable` | `` |
| index | `sqlite_autoindex_cursorDiskKV_1` | `cursorDiskKV` | `` |
| table | `ItemTable` | `ItemTable` | `CREATE TABLE ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)` |
| table | `cursorDiskKV` | `cursorDiskKV` | `CREATE TABLE cursorDiskKV (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB)` |

### Tables and columns

#### `ItemTable`

| cid | name | type | notnull | dflt_value | pk |
| --- | --- | --- | --- | --- | --- |
| 0 | `key` | `TEXT` | 0 | `None` | 0 |
| 1 | `value` | `BLOB` | 0 | `None` | 0 |

#### `cursorDiskKV`

| cid | name | type | notnull | dflt_value | pk |
| --- | --- | --- | --- | --- | --- |
| 0 | `key` | `TEXT` | 0 | `None` | 0 |
| 1 | `value` | `BLOB` | 0 | `None` | 0 |

### Foreign keys

(none)

---
