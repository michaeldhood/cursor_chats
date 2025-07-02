---
id: 2.2
title: "Extraction Core Logic"
status: pending
priority: high
feature: Foundation
dependencies: [2.1]
assigned_agent: null
created_at: "2025-06-07T23:49:29Z"
started_at: null
completed_at: null
error_log: null
---

## Description

Build the core extraction engine with configurable output paths and file processing logic.

## Details

- Implement `extract_chats()` function that processes discovered files
- Create configurable output directory structure and naming conventions
- Add file reading and JSON extraction from Cursor chat format
- Implement streaming processing for large files to manage memory
- Create output file generation with proper formatting and structure
- Add metadata preservation (timestamps, file origins, etc.)
- Support different output formats (JSON, JSONL, structured directories)
- Implement transaction-like processing (all-or-nothing extraction)
- Add extraction statistics and summary reporting

## Test Strategy

- Test extraction produces valid output files from sample chats
- Verify configurable output paths create proper directory structures
- Test streaming processing handles large files without memory issues
- Confirm metadata is preserved accurately in extracted files
- Validate different output formats produce expected results
- Test transaction processing rolls back on failures
- Verify extraction statistics are accurate and useful

## Follow-up Context

**Parent Task:** Task 2 - Chat Extraction Engine
**Trigger:** Task expansion for better manageability
**Relationship:** Core processing logic that extracts data from discovered files
