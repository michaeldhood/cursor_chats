## Cursor Chat Storage Architecture Diagrams (Old vs Modern)

This document provides **two architectures** (Old vs Modern) and **three diagram types for each**:

- **Diagram Type A**: Storage layout (filesystem + DBs)
- **Diagram Type B**: Dataflow (how a chat is reconstructed)
- **Diagram Type C**: Key-space / entities (what lives where)

Notes:

- “Old” here refers to the earlier pattern where **workspace-local `state.vscdb`** generally contained enough information to reconstruct conversations without a global join.
- “Modern” refers to Cursor’s split model where **workspace DBs contain metadata/indices** and **global DB contains the content**, sometimes in **headers + per-bubble blobs**.

---

## Old Architecture

### Diagram A (Old): Storage Layout

```mermaid
flowchart TD
  userHome["UserHome"] --> cursorUserDir["Cursor/User"]
  cursorUserDir --> workspaceStorage["workspaceStorage/"]
  workspaceStorage --> wsHashDir["<workspace_hash>/"]
  wsHashDir --> wsStateDb["state.vscdb"]
  wsHashDir --> wsJson["workspace.json"]

  wsStateDb --> wsItemTable["ItemTable (workspace-local)"]
  wsItemTable --> wsChatKeys["chat-related keys"]
  wsChatKeys --> inlineContent["Inline conversation content (typical)"]
```

### Diagram B (Old): Dataflow (Reconstruct Chat)

```mermaid
sequenceDiagram
  participant Reader as WorkspaceReader
  participant WsDB as WorkspaceStateVscdb

  Reader->>WsDB: Query ItemTable for chat-related keys
  WsDB-->>Reader: JSON blobs (metadata + messages)
  Reader->>Reader: Parse JSON and normalize
  Reader-->>Reader: Chat(thread) + messages ready to display/export
```

### Diagram C (Old): Entities / Key-Space View

```mermaid
flowchart LR
  subgraph workspaceDB_Old [Workspace state.vscdb (Old)]
    itemTableOld["ItemTable"]
    itemTableOld --> chatMetaOld["chat metadata keys"]
    itemTableOld --> chatMsgsOld["conversation/messages (inline JSON)"]
    itemTableOld --> uiStateOld["other UI state"]
  end

  chatMetaOld --> chatMsgsOld
```

---

## Modern Architecture

### Diagram A (Modern): Storage Layout (Workspace + Global)

```mermaid
flowchart TD
  userHome2["UserHome"] --> cursorUserDir2["Cursor/User"]
  cursorUserDir2 --> workspaceStorage2["workspaceStorage/"]
  cursorUserDir2 --> globalStorage2["globalStorage/"]

  workspaceStorage2 --> wsHashDir2["<workspace_hash>/"]
  wsHashDir2 --> wsStateDb2["state.vscdb"]
  wsHashDir2 --> wsJson2["workspace.json"]

  globalStorage2 --> globalStateDb["state.vscdb"]

  wsStateDb2 --> wsItemTable2["ItemTable (workspace)"]
  wsItemTable2 --> composerHeads["composer.composerData (heads/index)"]

  globalStateDb --> cursorDiskKV["cursorDiskKV (global KV)"]
  cursorDiskKV --> composerDataKey["composerData:{composerId}"]
  cursorDiskKV --> bubbleKey["bubbleId:{composerId}:{bubbleId}"]
```

### Diagram B (Modern): Dataflow (Reconstruct Chat with Bubble Split)

```mermaid
sequenceDiagram
  participant WsReader as WorkspaceStateReader
  participant GlReader as GlobalComposerReader
  participant WsDB as WorkspaceStateVscdb
  participant GlDB as GlobalStateVscdb

  WsReader->>WsDB: Read composer.composerData (heads)
  WsDB-->>WsReader: List of composers + metadata (titles, timestamps, modes)
  WsReader->>WsReader: Build composerId -> workspace attribution

  GlReader->>GlDB: Fetch composerData:{composerId}
  GlDB-->>GlReader: Composer JSON

  alt legacyInlineConversation
    GlReader-->>GlReader: Use conversation[] directly
  else splitConversation
    GlReader-->>GlReader: Read fullConversationHeadersOnly[]
    GlReader->>GlDB: Fetch bubbleId:{composerId}:{bubbleId} (batch)
    GlDB-->>GlReader: Bubble JSON blobs (text/richText)
    GlReader-->>GlReader: Merge headers + bubble content
  end

  GlReader-->>WsReader: Normalized conversation messages
  WsReader-->>WsReader: Attach workspace metadata (title/mode/path)
```

### Diagram C (Modern): Entities / Key-Space View

```mermaid
flowchart LR
  subgraph workspaceDB_Modern [Workspace state.vscdb (Modern)]
    itemTableModern["ItemTable"]
    itemTableModern --> composerHeadsModern["composer.composerData (heads)"]
    composerHeadsModern --> composerIdRefs["composerId references"]
  end

  subgraph globalDB_Modern [Global state.vscdb (Modern)]
    cursorDiskKVModern["cursorDiskKV"]
    cursorDiskKVModern --> composerDataModern["composerData:{composerId}"]
    composerDataModern --> conversationInlineModern["conversation[] (sometimes)"]
    composerDataModern --> headersOnlyModern["fullConversationHeadersOnly[] (sometimes)"]
    cursorDiskKVModern --> bubbleDataModern["bubbleId:{composerId}:{bubbleId}"]
  end

  composerIdRefs --> composerDataModern
  headersOnlyModern --> bubbleDataModern
```

---

## Appendix: Quick “Old vs Modern” Mental Model (ASCII)

<!-- 0----+----1----+----2----+----3----+----4----+----5----+----6----+----7----+ -->
<!-- Box width target: 74 characters between pipes -->

### Old (Workspace-centric)

┌──────────────────────────────────────────────────────────────────────────┐
│ workspaceStorage/<hash>/state.vscdb │
│ └─ ItemTable: chat keys → JSON blobs (metadata + inline messages) │
│ │
│ Reconstruct chat: read workspace DB → parse JSON → done │
└──────────────────────────────────────────────────────────────────────────┘

### Modern (Split: workspace metadata + global content)

┌──────────────────────────────────────────────────────────────────────────┐
│ workspaceStorage/<hash>/state.vscdb │
│ └─ ItemTable: composer.composerData → composerId “heads” + metadata │
│ │
│ globalStorage/state.vscdb │
│ └─ cursorDiskKV: │
│ - composerData:{composerId} → conversation OR headers-only │
│ - bubbleId:{composerId}:{bubbleId} → bubble content (split format) │
│ │
│ Reconstruct chat: workspace heads → fetch composerData → maybe fetch │
│ bubbles → merge → attach workspace attribution → done │
└──────────────────────────────────────────────────────────────────────────┘
