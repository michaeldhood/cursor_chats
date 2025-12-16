# Claude.ai Integration Setup

This guide explains how to configure the Claude.ai chat source for aggregation.

## Overview

The Claude.ai integration uses dlt (data load tool) to fetch conversations from Claude.ai's internal API with automatic incremental sync. Only conversations updated since the last sync are fetched.

## Prerequisites

1. A Claude.ai account with conversations
2. Access to your browser's DevTools to extract session cookies

## Configuration

### Option 1: dlt Secrets File (Recommended)

1. Copy the example secrets file:
   ```bash
   cp .dlt/secrets.toml.example .dlt/secrets.toml
   ```

2. Edit `.dlt/secrets.toml` and fill in your values:
   ```toml
   [sources.claude_conversations]
   org_id = "your-org-id-here"
   session_cookie = "your-session-cookie-here"
   ```

### Option 2: Environment Variables

Set these environment variables:
```bash
export CLAUDE_ORG_ID="your-org-id-here"
export CLAUDE_SESSION_COOKIE="your-session-cookie-here"
```

## Getting Your Organization ID

1. Go to https://claude.ai/settings/account
2. Look at the URL in your browser's address bar
3. Find the `organizationId` parameter: `?organizationId=YOUR-ORG-ID-HERE`
4. Copy the UUID value (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

Example URL:
```
https://claude.ai/settings/account?organizationId=5a6a80ed-8f4e-4041-9040-a76c57cd0b16
```
In this case, your org_id is `5a6a80ed-8f4e-4041-9040-a76c57cd0b16`

## Getting Your Session Cookie

### Chrome/Edge (Chromium)

1. Log into claude.ai in your browser
2. Open DevTools:
   - Press `F12` or `Ctrl+Shift+I` (Windows/Linux)
   - Press `Cmd+Option+I` (macOS)
3. Go to the **Application** tab (or **Storage** in Firefox)
4. In the left sidebar, expand **Cookies** → `https://claude.ai`
5. Find the cookie named `sessionKey`
6. Copy its **Value** (it's a long string)

### Firefox

1. Log into claude.ai in your browser
2. Open DevTools (`F12`)
3. Go to the **Storage** tab
4. Expand **Cookies** → `https://claude.ai`
5. Find `sessionKey` and copy its value

### Safari

1. Enable Developer menu: Safari → Preferences → Advanced → "Show Develop menu"
2. Log into claude.ai
3. Develop → Show Web Inspector
4. Storage tab → Cookies → `claude.ai`
5. Find `sessionKey` and copy its value

## Security Notes

⚠️ **Important**: Your session cookie is sensitive! It provides access to your Claude.ai account.

- **Never commit** `.dlt/secrets.toml` to version control
- The `.dlt/secrets.toml` file is already in `.gitignore`
- If you use environment variables, don't log them or share them
- Session cookies expire periodically - you may need to refresh them

## Usage

Once configured, ingest Claude conversations:

```bash
# Ingest only Claude.ai conversations
python -m src ingest --source claude

# Ingest both Cursor and Claude.ai
python -m src ingest --source all

# Ingest only Cursor (default)
python -m src ingest --source cursor
```

## How Incremental Sync Works

dlt automatically tracks the `updated_at` timestamp of the last synced conversation. On subsequent runs:

- Only conversations updated since the last sync are fetched
- State is stored in `.dlt/pipelines/claude_conversations/`
- You can delete this folder to force a full re-sync

## Troubleshooting

### "org_id must be provided" Error

- Check that your `.dlt/secrets.toml` file exists and has the correct section name
- Verify the `org_id` value is correct (UUID format)
- Try using environment variables instead

### "session_cookie must be provided" Error

- Make sure you copied the entire cookie value (it's very long)
- Check that you're logged into claude.ai in your browser
- The cookie may have expired - extract a fresh one

### "403 Forbidden" or Authentication Errors

- Your session cookie has expired - extract a new one
- Make sure you're copying the `sessionKey` cookie, not other cookies
- Verify you're logged into the correct Claude.ai account

### No Conversations Found

- Check that you have conversations in your Claude.ai account
- Verify your organization ID is correct
- Try deleting `.dlt/pipelines/claude_conversations/` to reset state

## API Rate Limits

Claude.ai may rate limit requests. If you encounter rate limiting:

- The integration will log errors but continue processing
- Wait a few minutes and try again
- dlt's incremental sync means you won't re-fetch already synced conversations

## Data Mapping

Claude conversations are mapped to the unified chat database:

| Claude.ai Field | Database Field |
|-----------------|----------------|
| `uuid` | `cursor_composer_id` (reused) |
| `name` | `title` |
| `created_at` | `created_at` |
| `updated_at` | `last_updated_at` |
| `chat_messages[].sender` | `messages[].role` |
| `chat_messages[].content[].text` | `messages[].text` |
| - | `source` = `"claude.ai"` |

## Related Documentation

- [Claude.ai Internal API Reference](claude-ai-internal-api-reference.md)
- [Database Schema](db-schema.md)

