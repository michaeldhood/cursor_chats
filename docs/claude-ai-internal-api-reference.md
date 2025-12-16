# Claude.ai Internal API Reference

> **Disclaimer**: This documents Claude.ai's internal/undocumented API endpoints discovered through browser DevTools inspection. These are NOT official public APIs and may change without notice. Use at your own risk.

**Last Updated**: 2025-12-15

---

## Overview

Claude.ai uses a REST API for its web interface. Authentication is handled via session cookies (not API keys like the public Anthropic API).

### Base URLs

| URL | Purpose |
|-----|---------|
| `https://claude.ai/api/organizations/{ORG_ID}/` | Main application API |
| `https://a-api.anthropic.com/v1/` | Analytics/Telemetry |
| `https://statsig.anthropic.com/` | Feature flags |
| `https://api.honeycomb.io/` | Observability (traces) |

### Authentication

All requests require valid session cookies. The browser automatically includes these via `credentials: 'include'`.

### Organization ID

Found at: `https://claude.ai/settings/account`

The URL contains your org ID: `?organizationId=YOUR-ORG-ID-HERE`

---

## Endpoints

### Conversations

#### List All Conversations

```http
GET /api/organizations/{ORG_ID}/chat_conversations
```

**Response**: Array of conversation metadata objects

```json
[
  {
    "uuid": "conv-uuid-here",
    "name": "Conversation Title",
    "model": "claude-sonnet-4-5-20250929",
    "created_at": "2025-12-15T...",
    "updated_at": "2025-12-15T...",
    "summary": "Brief summary..."
  }
]
```

#### Get Single Conversation (Full)

```http
GET /api/organizations/{ORG_ID}/chat_conversations/{CONV_ID}?tree=True&rendering_mode=messages&render_all_tools=true&consistency=eventual
```

**Query Parameters**:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `tree` | `True` | Include full message tree (supports branching conversations) |
| `rendering_mode` | `messages` | Format response as message objects |
| `render_all_tools` | `true` | Include tool use and artifact data |
| `consistency` | `eventual` | Database consistency level |

---

### Create Conversation

```http
POST /api/organizations/{ORG_ID}/chat_conversations
```

**Request Body**:
```json
{
  "uuid": "65e52d57-3b0a-4a64-af2d-bd8cf69471ec",
  "name": "",
  "model": "claude-opus-4-5-20251101",
  "include_conversation_preferences": true,
  "is_temporary": false
}
```

> **Note**: The client generates the UUID before sending!

**Response** (201 Created): Returns full conversation object with settings populated.

---

### Send Message (Completion)

```http
POST /api/organizations/{ORG_ID}/chat_conversations/{CONV_ID}/completion
Content-Type: application/json
Accept: text/event-stream
```

**Request Body**:
```json
{
  "prompt": "tell me about myself",
  "parent_message_uuid": "00000000-0000-4000-8000-000000000000",
  "attachments": [],
  "files": [],
  "locale": "en-US",
  "model": "claude-opus-4-5-20251101",
  "personalized_styles": [...],
  "rendering_mode": "messages",
  "sync_sources": [],
  "timezone": "America/Los_Angeles",
  "tools": [...]
}
```

**Request Fields**:

| Field | Description |
|-------|-------------|
| `prompt` | The user's message text |
| `parent_message_uuid` | Parent message for threading (root = `00000000-0000-4000-8000-000000000000`) |
| `model` | Model to use |
| `personalized_styles` | Array of style prompts (from `/list_styles`) |
| `tools` | Array of available MCP tools |
| `locale` | User locale (e.g., `en-US`) |
| `timezone` | User timezone (e.g., `America/Los_Angeles`) |
| `rendering_mode` | Response format (`messages`) |
| `attachments` / `files` | File attachments |
| `sync_sources` | Synced data sources |

**Response**: Server-Sent Events (SSE) stream

---

### SSE Event Types (Streaming Response)

The completion endpoint returns a stream of Server-Sent Events:

#### 1. `message_start`
```json
{
  "type": "message_start",
  "message": {
    "id": "chatcompl_01KrjHdBA8ZHTy3KgHb4BNPi",
    "type": "message",
    "role": "assistant",
    "model": "",
    "parent_uuid": "019b24c7-2cc3-7334-91a4-7cc2d6cb69b7",
    "uuid": "019b24c7-2cc3-7334-91a4-7cc39fd26d11",
    "content": [],
    "stop_reason": null,
    "trace_id": "fe37d70d310c2c6eb18d941f06e1eb41",
    "request_id": "req_011CW9Vxhig8TuFeYV3avU51"
  }
}
```

#### 2. `content_block_start`
```json
{
  "type": "content_block_start",
  "index": 0,
  "content_block": {
    "start_timestamp": "2025-12-16T01:29:56.092205Z",
    "type": "thinking",  // or "text"
    "thinking": "",
    "summaries": []
  }
}
```

#### 3. `content_block_delta`

For thinking (extended thinking visible!):
```json
{"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "Mike is asking..."}}
```

For thinking summaries:
```json
{"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_summary_delta", "summary": {"summary": "Thinking about..."}}}
```

For text output:
```json
{"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "Hey Mike!"}}
```

#### 4. `content_block_stop`
```json
{"type": "content_block_stop", "index": 1, "stop_timestamp": "2025-12-16T01:30:03.164090Z"}
```

#### 5. `message_delta`
```json
{"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": null}}
```

#### 6. `message_limit` (Rate Limiting!)
```json
{
  "type": "message_limit",
  "message_limit": {
    "type": "within_limit",
    "remaining": null,
    "representativeClaim": "five_hour",
    "overageDisabledReason": "org_level_disabled",
    "overageInUse": false,
    "windows": {
      "5h": {"status": "within_limit", "resets_at": 1765864800, "utilization": 0.384},
      "7d": {"status": "within_limit", "resets_at": 1766451600, "utilization": 0.042}
    }
  }
}
```

#### 7. `message_stop`
```json
{"type": "message_stop"}
```

---

### Get Conversation

**Response**: Full conversation object with messages

```json
{
  "uuid": "f61c2459-c781-4895-a7f4-dc34aa0871d8",
  "name": "DIY personalized toy chests for kids",
  "summary": "**Conversation Overview**\n\nThe user initiated...",
  "model": "claude-opus-4-5-20251101",
  "created_at": "2025-12-15T20:48:31.226131+00:00",
  "updated_at": "2025-12-15T20:52:38.031888+00:00",
  "settings": {
    "enabled_web_search": true,
    "enabled_sourdough": true,
    "enabled_foccacia": true,
    "enabled_mcp_tools": { ... },
    "enabled_monkeys_in_a_barrel": true,
    "enabled_saffron": true,
    "preview_feature_uses_artifacts": true,
    "enabled_artifacts_attachments": true,
    "enabled_turmeric": true
  },
  "is_starred": false,
  "is_temporary": false,
  "platform": "CLAUDE_AI",
  "current_leaf_message_uuid": "019b23c9-136d-7772-a6fa-df41ec92c314",
  "chat_messages": [...]
}
```

**Conversation Fields**:

| Field | Description |
|-------|-------------|
| `uuid` | Unique conversation identifier |
| `name` | Auto-generated or user-set title |
| `summary` | AI-generated conversation summary |
| `model` | Model used (e.g., `claude-opus-4-5-20251101`) |
| `settings` | Per-conversation feature settings |
| `is_starred` | User starred this conversation |
| `is_temporary` | Temporary/ephemeral conversation |
| `platform` | Source platform (`CLAUDE_AI`) |
| `current_leaf_message_uuid` | Points to active branch tip |

**Settings Object** (Feature Flags per Conversation):

| Setting | Description |
|---------|-------------|
| `enabled_web_search` | Web search capability |
| `enabled_sourdough` | Unknown feature (codename) |
| `enabled_foccacia` | Unknown feature (codename) |
| `enabled_mcp_tools` | MCP tool integrations (see below) |
| `enabled_monkeys_in_a_barrel` | Unknown feature (codename) |
| `enabled_saffron` | Unknown feature (codename) |
| `enabled_turmeric` | Unknown feature (codename) |
| `preview_feature_uses_artifacts` | Artifacts enabled |
| `enabled_artifacts_attachments` | Artifact attachments enabled |

**Message Object**:

```json
{
  "uuid": "019b23c5-a781-707a-a9db-8321f243db2d",
  "text": "",
  "content": [
    {
      "start_timestamp": "2025-12-15T20:48:37.128896+00:00",
      "stop_timestamp": "2025-12-15T20:48:48.377516+00:00",
      "type": "text",
      "text": "Great idea! A personalized toy chest...",
      "citations": []
    }
  ],
  "sender": "assistant",
  "index": 1,
  "created_at": "2025-12-15T20:48:48.504392+00:00",
  "updated_at": "2025-12-15T20:48:48.504392+00:00",
  "truncated": false,
  "stop_reason": "stop_sequence",
  "attachments": [],
  "files": [],
  "files_v2": [],
  "sync_sources": [],
  "parent_message_uuid": "019b23c5-a780-7103-9cb5-e5b2baa1c1cb"
}
```

**Message Fields**:

| Field | Description |
|-------|-------------|
| `uuid` | Unique message identifier |
| `sender` | `human` or `assistant` |
| `index` | Message order in conversation |
| `content[].start_timestamp` | When streaming started |
| `content[].stop_timestamp` | When streaming ended |
| `content[].type` | Content type (`text`, etc.) |
| `content[].citations` | Source citations array |
| `stop_reason` | Why model stopped (`stop_sequence`, `max_tokens`, etc.) |
| `truncated` | Whether message was truncated |
| `files` / `files_v2` | Attached files (images, etc.) |
| `parent_message_uuid` | Parent for branching conversations |

---

### Artifacts

#### List Published Artifacts

```http
GET /api/organizations/{ORG_ID}/published_artifacts?include_deleted_artifacts=false
```

**Query Parameters**:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `include_deleted_artifacts` | `true/false` | Whether to include soft-deleted artifacts |

**Response**:
```json
[
    {
        "artifact_identifier": "remixed-4cb000a6",
        "artifact_type": "text/html",
        "code_language": null,
        "message_uuid": "019a8837-d7ad-70fd-ad57-06ad20c5dd10",
        "title": "first-orchard-dice.html",
        "artifact_version_uuid": null,
        "published_artifact_uuid": "c409f6bc-1d04-435f-9159-0b7b7bf73d65",
        "deleted": false,
        "chat_conversation_uuid": "a874eec4-8c49-4893-8032-d1d561ed952d"
    }
]
```

**Artifact Object Fields**:

| Field | Description |
|-------|-------------|
| `artifact_identifier` | Unique slug/identifier |
| `artifact_type` | MIME type (`text/html`, `text/markdown`, etc.) |
| `code_language` | Programming language for code artifacts |
| `message_uuid` | The message that created this artifact |
| `title` | Display title |
| `published_artifact_uuid` | Unique ID for published version |
| `deleted` | Soft delete flag |
| `chat_conversation_uuid` | Parent conversation |

#### Get Artifact Versions

```http
GET /api/organizations/{ORG_ID}/artifacts/{ARTIFACT_ID}/versions?source=w
```

**Query Parameters**:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `source` | `w` | Source context (likely `w` = web/workspace) |

---

### Projects

#### Sync Project State

```http
POST /api/organizations/{ORG_ID}/projects/{PROJECT_ID}/sync
```

**Response Status**: `202 Accepted`

#### List Files in Project/Conversation

```http
GET /api/organizations/{ORG_ID}/conversations/{CONV_ID}/wiggle/list-files?prefix=
```

**Query Parameters**:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `prefix` | `""` | Filter files by prefix (empty = all) |

---

### Settings & Configuration

#### Feature Settings

```http
GET /api/organizations/{ORG_ID}/feature_settings
```

**Response**:
```json
{
    "disabled_features": ["haystack", "dxt_allowlist"],
    "forced_settings": [
        {"feature": "haystack", "forced_state": false},
        {"feature": "thumbs", "forced_state": true}
    ]
}
```

**Known Features**:
| Feature | Description |
|---------|-------------|
| `haystack` | Unknown - possibly search/retrieval system |
| `dxt_allowlist` | Unknown - possibly extension/tool allowlist |
| `thumbs` | Thumbs up/down feedback buttons |

#### List Styles (Response Styles)

```http
GET /api/organizations/{ORG_ID}/list_styles
```

Returns Claude's built-in response styles with their **actual system prompts**!

**Response Structure**:
```json
{
    "defaultStyles": [...],
    "customStyles": [],
    "text": {"tooltip": "", "inlineNotice": ""}
}
```

**Built-in Styles**:

| Key | Name | Description |
|-----|------|-------------|
| `Default` | Normal | Default responses from Claude |
| `Learning` | Learning | Socratic teaching style with 7 principles |
| `Concise` | Concise | Shorter responses, "Concise Mode" |
| `Explanatory` | Explanatory | Teacher-like thorough explanations |
| `Formal` | Formal | Business/professional style |

**Style Object Structure**:
```json
{
    "type": "default",
    "key": "Concise",
    "name": "Concise",
    "nameKey": "concise_style_name",
    "prompt": "Claude is operating in Concise Mode...",  // The actual system prompt!
    "summary": "Shorter responses & more messages",
    "summaryKey": "concise_style_summary",
    "isDefault": false
}
```

> **Notable**: The `prompt` field contains the actual system prompt injected when that style is active. This is how Claude's personality/behavior changes per style.

---

### Files API

```http
GET /api/{ORG_ID}/files/{FILE_UUID}/thumbnail
GET /api/{ORG_ID}/files/{FILE_UUID}/preview
```

Used for image attachments in conversations.

**File Object Structure** (from message attachments):

```json
{
  "file_kind": "image",
  "file_uuid": "db0329df-f892-429e-9874-626d868e0a1d",
  "file_name": "1765831929353_image.png",
  "created_at": "2025-12-15T20:52:09.931003+00:00",
  "thumbnail_url": "/api/{ORG_ID}/files/{FILE_UUID}/thumbnail",
  "preview_url": "/api/{ORG_ID}/files/{FILE_UUID}/preview",
  "thumbnail_asset": {
    "url": "...",
    "file_variant": "thumbnail",
    "primary_color": "060606",
    "image_width": 350,
    "image_height": 328
  },
  "preview_asset": {
    "url": "...",
    "file_variant": "preview",
    "primary_color": "060606",
    "image_width": 350,
    "image_height": 328
  }
}
```

---

### MCP Tools Integration

Claude.ai supports MCP (Model Context Protocol) tool integrations. Enabled tools are stored per-conversation in `settings.enabled_mcp_tools`:

```json
{
  "enabled_mcp_tools": {
    "": true,
    "local:Notion:fetch-76193f5121ed8a2cb3045cd78e7a7a82": true,
    "local:Linear:list_issues-d7479ef02d0dd8d28c5048e12c941bf4": true,
    "local:Filesystem:write_file-0683fe3ad60ce34728a5d49a04e33c8b": true,
    "local:Context7:get-library-docs-93fa5b06323efa86c778d9d37aaa9db9": true,
    "c06b83b5-613c-484d-a1c0-e5573bc3499c:search-7592b6b6a8ebd259475a1531680bfc6e": true
  }
}
```

**Tool ID Format**:
- Local tools: `local:{SERVER}:{TOOL}-{HASH}`
- Remote tools: `{UUID}:{TOOL}-{HASH}`

**Known MCP Servers** (from user data):
- Notion
- Linear
- Filesystem
- Context7

---

### User Preferences & Settings

```http
GET /api/organizations/{ORG_ID}/settings
GET /api/organizations/{ORG_ID}/preferences
GET /api/organizations/{ORG_ID}/bootstrap
```

---

### Integrations

#### Google Drive Sync

```http
GET /api/organizations/{ORG_ID}/sync/ingestion/gdrive/progress
```

Tracks Google Drive file ingestion progress.

---

### Models

Model information endpoints (observed in network traffic):

```http
GET /api/organizations/{ORG_ID}/claude-sonnet-4-5-20250929
GET /api/organizations/{ORG_ID}/claude-opus-4-5-20251101
```

---

### Misc Endpoints

```http
GET /api/organizations/{ORG_ID}/spotlight           # Search/spotlight feature
GET /api/organizations/{ORG_ID}/check_3ds_required  # 3D Secure payment check
GET /api/organizations/{ORG_ID}/claude_web?locale=en-US
GET /api/organizations/{ORG_ID}/ping                # Health check
GET /api/organizations/{ORG_ID}/progress            # General progress tracking
```

Single-letter endpoints (purpose unclear):
```http
/i    # Unknown
/p    # Unknown  
/t    # Unknown
```

---

### Analytics Endpoints (a-api.anthropic.com)

These appear to be analytics/telemetry endpoints:

```http
POST /v1/m    # Metrics
POST /v1/t    # Tracking events
POST /v1/p    # Page views / interactions
POST /v1/i    # Impressions?
```

---

## API Tree Structure

```
claude.ai/api/organizations/{ORG_ID}/
│
├── chat_conversations/                         # POST: Create conversation
│   └── {CONV_ID}
│       ├── ?tree=True&rendering_mode=messages&render_all_tools=true&consistency=eventual  # GET
│       └── /completion                         # POST: Send message (SSE stream)
│
├── conversations/{CONV_ID}/
│   └── wiggle/
│       └── list-files?prefix=
│
├── artifacts/{ARTIFACT_ID}/
│   └── versions?source=w
│
├── published_artifacts?include_deleted_artifacts=false
│
├── projects/{PROJECT_ID}/
│   └── sync
│
├── files/{FILE_UUID}/
│   ├── thumbnail
│   └── preview
│
├── sync/
│   └── ingestion/
│       └── gdrive/
│           └── progress
│
├── feature_settings
├── list_styles
├── settings
├── preferences
├── bootstrap
│
├── claude-sonnet-4-5-20250929      # Model info
├── claude-opus-4-5-20251101        # Model info
│
├── spotlight
├── check_3ds_required
├── claude_web?locale=en-US
├── ping
├── progress
│
└── i, p, t                         # Single-letter endpoints


a-api.anthropic.com/v1/
├── m    # Metrics
├── t    # Tracking
├── p    # Page views
└── i    # Impressions?
```

---

---

## Appendix: Claude's Built-in Style Prompts

These are the actual system prompts used by Claude's different response styles (extracted from `/list_styles`):

### Learning Style Prompt

```
The goal is not just to provide answers, but to help students develop robust 
understanding through guided exploration and practice. Follow these principles. 
You do not need to use all of them! Use your judgement on when it makes sense 
to apply one of the principles.

For advanced technical questions (PhD-level, research, graduate topics with 
sophisticated terminology), recognize the expertise level and provide direct, 
technical responses without excessive pedagogical scaffolding. Skip principles 
1-3 below for such queries.

1. Use leading questions rather than direct answers. Ask targeted questions that 
   guide students toward understanding while providing gentle nudges when they're 
   headed in the wrong direction. Balance between pure Socratic dialogue and 
   direct instruction.

2. Break down complex topics into clear steps. Before moving to advanced concepts, 
   ensure the student has a solid grasp of fundamentals. Verify understanding at 
   each step before progressing.

3. Start by understanding the student's current knowledge:
   - Ask what they already know about the topic
   - Identify where they feel stuck
   - Let them articulate their specific points of confusion

4. Make the learning process collaborative:
   - Engage in two-way dialogue
   - Give students agency in choosing how to approach topics
   - Offer multiple perspectives and learning strategies
   - Present various ways to think about the concept

5. Adapt teaching methods based on student responses:
   - Offer analogies and concrete examples
   - Mix explaining, modeling, and summarizing as needed
   - Adjust the level of detail based on student comprehension
   - For expert-level questions, match the technical sophistication expected

6. Regularly check understanding by asking students to:
   - Explain concepts in their own words
   - Articulate underlying principles
   - Provide their own examples
   - Apply concepts to new situations

7. Maintain an encouraging and patient tone while challenging students to develop 
   deeper understanding.
```

### Concise Style Prompt

```
Claude is operating in Concise Mode. In this mode, Claude aims to reduce its 
output tokens while maintaining its helpfulness, quality, completeness, and accuracy.

Claude provides answers to questions without much unneeded preamble or postamble. 
It focuses on addressing the specific query or task at hand, avoiding tangential 
information unless helpful for understanding or completing the request. If it 
decides to create a list, Claude focuses on key information instead of 
comprehensive enumeration.

Claude maintains a helpful tone while avoiding excessive pleasantries or redundant 
offers of assistance.

Claude provides relevant evidence and supporting details when substantiation is 
helpful for factuality and understanding of its response. For numerical data, 
Claude includes specific figures when important to the answer's accuracy.

For code, artifacts, written content, or other generated outputs, Claude maintains 
the exact same level of quality, completeness, and functionality as when NOT in 
Concise Mode. There should be no impact to these output types.

Claude does not compromise on completeness, correctness, appropriateness, or 
helpfulness for the sake of brevity.

If the human requests a long or detailed response, Claude will set aside Concise 
Mode constraints and provide a more comprehensive answer.

If the human appears frustrated with Claude's conciseness, repeatedly requests 
longer or more detailed responses, or directly asks about changes in Claude's 
response style, Claude informs them that it's currently in Concise Mode and 
explains that Concise Mode can be turned off via Claude's UI if desired. Besides 
these scenarios, Claude does not mention Concise Mode.
```

### Explanatory Style Prompt

```
Claude aims to give clear, thorough explanations that help the human deeply 
understand complex topics.

Claude approaches questions like a teacher would, breaking down ideas into easier 
parts and building up to harder concepts. It uses comparisons, examples, and 
step-by-step explanations to improve understanding.

Claude keeps a patient and encouraging tone, trying to spot and address possible 
points of confusion before they arise. Claude may ask thinking questions or suggest 
mental exercises to get the human more involved in learning.

Claude gives background info when it helps create a fuller picture of the topic. 
It might sometimes branch into related topics if they help build a complete 
understanding of the subject.

When writing code or other technical content, Claude adds helpful comments to 
explain the thinking behind important steps.

Claude always writes prose and in full sentences, especially for reports, documents, 
explanations, and question answering. Claude can use bullets only if the user asks 
specifically for a list.
```

### Formal Style Prompt

```
Claude aims to write in a clear, polished way that works well for business settings.

Claude structures its answers carefully, with clear sections and logical flow. It 
gets to the point quickly while giving enough detail to fully answer the question.

Claude uses a formal but clear tone, avoiding casual language and slang. It writes 
in a way that would be appropriate for sharing with colleagues and stakeholders.

Claude balances being thorough with being efficient. It includes important context 
and details while leaving out unnecessary information that might distract from the 
main points.

Claude writes prose and in full sentences, especially for reports, documents, 
explanations, and question answering. Claude can use bullet points or lists only 
if the human asks specifically for a list, or if it makes sense for the specific 
task that the human is asking about.
```

---

## Internal Codenames

Claude.ai uses food-themed and playful codenames for features:

### Enabled Features
| Codename | Likely Feature | Value |
|----------|----------------|-------|
| `sourdough` | Unknown | `true` |
| `foccacia` | Unknown | `true` |
| `saffron` | Unknown | `true` |
| `turmeric` | Unknown | `true` |
| `monkeys_in_a_barrel` | Unknown | `true` |
| `paprika_mode` | Extended features? | `"extended"` |
| `wiggle` | File management system | Active |

### Disabled/Null Features
| Codename | Likely Feature | Status |
|----------|----------------|--------|
| `bananagrams` | Unknown | `null` |
| `compass` | Navigation/search? | `null` |
| `compass_mode` | Compass modes | `null` |
| `create_mode` | Creation modes | `null` |
| `haystack` | Search/retrieval? | Disabled |
| `dxt_allowlist` | Extension allowlist? | Disabled |
| `enabled_drive_search` | Google Drive search | `null` |
| `preview_feature_uses_latex` | LaTeX rendering | `null` |
| `preview_feature_uses_citations` | Citation support | `null` |
| `has_sensitive_data` | PII/sensitive data flag | `null` |

---

## Rate Limiting

Claude.ai uses a sliding window rate limiting system:

| Window | Description |
|--------|-------------|
| `5h` | 5-hour rolling window |
| `7d` | 7-day rolling window |

**Rate Limit Response Fields**:
- `status`: `within_limit` or limit status
- `resets_at`: Unix timestamp when window resets
- `utilization`: Percentage of limit used (0.0 - 1.0)
- `representativeClaim`: Claim type (`five_hour`)
- `overageInUse`: Whether overage billing is active

---

## Unknown / To Investigate

- [x] ~~`POST` endpoints for creating conversations/messages~~ ✅ Found!
- [x] ~~How messages are sent~~ ✅ SSE streaming via `/completion`
- [ ] Artifact CRUD operations (create, update, delete)
- [ ] Project file upload endpoint (related to `wiggle/`)
- [ ] What `sourdough`, `foccacia`, `saffron`, `turmeric` features do
- [ ] What `monkeys_in_a_barrel` feature does
- [ ] What `haystack` feature does (search?)
- [ ] What `dxt_allowlist` feature does (extensions?)
- [ ] What `paprika_mode: "extended"` enables
- [ ] What `bananagrams` feature does
- [ ] Single-letter endpoints (`/i`, `/p`, `/t`) purpose
- [ ] Team/workspace management endpoints

---

## Related Tools

### Chrome Extension: Claude-Conversation-Exporter

A Chrome extension that uses these endpoints to export conversations:
- GitHub: https://github.com/socketteer/Claude-Conversation-Exporter
- Exports to JSON, Markdown, Plain Text
- Preserves model information
- Supports bulk export

---

## Security Notes

1. **Session-based auth**: Uses cookies, not API keys
2. **CORS protected**: Requests must come from claude.ai origin
3. **Rate limiting**: Likely enforced but limits unknown
4. **Cloudflare protection**: Anti-bot measures on login

---

## Changelog

- **2025-12-15**: Initial documentation based on DevTools inspection

