# Project: Cursor Chats Knowledge Base

## Overview

Turn Cursor chat logs into a dynamic knowledge base that helps users capture insights, track project evolution, journal decisions, and maintain context across sessions.

## Metadata

- **Project ID**: cursor-chats
- **Status**: active
- **Created**: 2025-06-06T22:57:08Z
- **Last Updated**: 2025-07-05T00:00:00Z
- **Lead**: Development Team
- **Progress**: 3 tasks completed (2.2, 4, 6.3)

## Purpose

This project creates a comprehensive system that extracts knowledge from Cursor chat logs, enabling users to:

- Build searchable archives of development conversations
- Generate structured journals and insights
- Maintain context across AI sessions
- Feed durable context back to Cursor for better assistance
- Add playful memory features to avoid repetitive questions

## Scope

### In Scope

- Chat log extraction and parsing
- Knowledge extraction and tagging
- Journal generation with templates
- Search functionality across chat archives
- Memory bank for context retention
- Timeline views of project evolution
- AI-powered summarization and insights
- Collaboration features for teams
- Humorous responses for repeated questions

### Out of Scope

- Real-time chat monitoring during active sessions
- Integration with other chat platforms (Slack, Discord, etc.)
- Advanced NLP that requires specialized hardware
- Commercial licensing or white-label solutions

## Key Deliverables

- **Phase 1**: Core extraction, parsing, and journaling system
- **Phase 2**: Knowledge extraction, memory bank, and search functionality
- **Phase 3**: AI insights, visualizations, and collaboration tools

## Dependencies

- Python 3.8+ environment
- Access to Cursor chat log files
- Optional: AI API integration (xAI, OpenAI, etc.)
- Optional: Linear API for task management via MCP server

## Related Projects

- Task Magic system (project management framework)
- MCP server integration for Linear workflow

## Notes

The project includes a unique "comical memory" feature where Cursor playfully responds to repeated questions, encouraging users to document their learnings. The system grows from a basic extractor into a sophisticated knowledge management platform.

### Recent Updates (2025-07-05)

Completed implementations:
- **Task 2.2 (CUR-1)**: Added customizable output paths to the extraction core logic
- **Task 4 (CUR-5)**: Implemented basic tagging system for organizing extracted chats
- **Task 6.3 (CUR-11, CUR-12)**: Added batch processing with --all flag and replaced print statements with proper logging
