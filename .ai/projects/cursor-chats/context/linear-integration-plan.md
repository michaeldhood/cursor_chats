# PRD: Linear Integration for Cursor Chats

## 1. Product overview

### 1.1 Document title and version

- PRD: Linear Integration for Cursor Chats
- Version: 1.0

### 1.2 Product summary

This feature plan details the integration of the Cursor Chats Knowledge Base project with Linear for task management through the existing MCP server. The integration enables seamless task tracking across three development phases, with 40 structured issues organized into 12 milestones across 3 projects.

## 2. Goals

### 2.1 Business goals

- Streamline task management for the Cursor Chats project
- Leverage existing MCP server infrastructure for Linear integration
- Enable continuous communication between Cursor and Linear for task updates
- Track development progress across three distinct phases

### 2.2 User goals

- Automatically fetch and complete tasks through Linear API integration
- Maintain visibility into project progress through Linear's interface
- Enable team collaboration through shared task tracking
- Automate task state updates based on development progress

### 2.3 Non-goals

- Creating a new MCP server (leverage existing infrastructure)
- Replacing Linear with another task management system
- Manual task synchronization processes
- Integration with other project management tools

## 3. Linear Structure

### 3.1 Team Organization

**Team: Cursor**

- All cursor_chats development tracked within the "Cursor" team in Linear
- Utilizes existing MCP server for continuous Cursor ↔ Linear communication
- Bot user "Cursor" assigned to handle automated task updates

### 3.2 Project Structure

**Project 1: Phase 1 - Foundation**

- Description: Build the core extraction, parsing, and journaling functionality
- Duration: 2-3 months
- Milestones: 4 (Extraction Enhancements, Improved Parsing, Journaling Functionality, CLI Usability)
- Issues: CUR-1 through CUR-13

**Project 2: Phase 2 - Knowledge Extraction and Memory**

- Description: Add knowledge extraction, durable context, and humorous memory features
- Duration: 2-3 months
- Milestones: 4 (Memory Bank, Timeline View, Enhanced Markdown, Search Functionality, Comical Memory)
- Issues: CUR-14 through CUR-28

**Project 3: Phase 3 - Advanced Features and Polish**

- Description: Introduce AI insights, visualizations, and collaboration tools
- Duration: 2-3 months
- Milestones: 4 (AI Summarization, Visualization, Collaboration, Enhanced Comical Elements)
- Issues: CUR-29 through CUR-40

## 4. MCP Server Integration Workflow

### 4.1 Task Fetching Process

- **Endpoint**: `GET /v1/issues?teamId=CURSOR&state=Todo`
- **Frequency**: Every 15 minutes via automated sync
- **Authentication**: API key provided to MCP server
- **Error Handling**: Retry mechanism on failure with exponential backoff

### 4.2 Task Assignment Logic

- Issues automatically assigned to "Cursor" bot user in Linear
- Assignment triggers MCP server notification to Cursor
- Task context and requirements made available to Cursor workspace
- Priority-based task selection (Critical → High → Medium → Low)

### 4.3 Task Completion Workflow

- **Endpoint**: `PUT /v1/issues/CUR-{id}` with state "Completed"
- **Trigger**: Cursor completes implementation and testing
- **Validation**: Automated checks ensure acceptance criteria met
- **Documentation**: Progress notes and artifacts attached to Linear issue

## 5. Issue Structure and Estimates

### 5.1 Effort Estimates

- **Small**: 1-2 days (e.g., documentation updates, simple configuration changes)
- **Medium**: 3-5 days (e.g., new feature implementation, API integration)
- **Large**: 1-2 weeks (e.g., AI integration, complex visualization features)

### 5.2 Sample Issues by Phase

**Phase 1 Examples:**

- CUR-1: Add customizable output paths and filenames (Medium)
- CUR-2: Optimize directory search depth (Small)
- CUR-8: Implement journal generation (Medium)

**Phase 2 Examples:**

- CUR-14: Extract and tag chat excerpts (Medium)
- CUR-23: Set up chat indexing (Medium)
- CUR-26: Track question repetition (Medium)

**Phase 3 Examples:**

- CUR-29: Select and integrate AI API (Large)
- CUR-33: Explore knowledge maps (Large)
- CUR-35: Develop team chat syncing (Large)

## 6. Implementation Details

### 6.1 Linear API Integration

```json
{
  "title": "CUR-1 - Add customizable output paths and filenames",
  "description": "Update extract_chats to accept user-defined output directories and prefixes for JSON files.",
  "teamId": "CURSOR",
  "projectId": "Phase 1 - Foundation",
  "milestoneId": "Extraction Enhancements",
  "estimate": "Medium",
  "priority": "High"
}
```

### 6.2 CSV Import Format

For bulk issue creation:

```csv
Title,Description,Project,Milestone,Estimate,Priority
"CUR-1 - Add customizable output paths","Update extract_chats to accept user-defined output...","Phase 1 - Foundation","Extraction Enhancements","Medium","High"
```

### 6.3 Workflow States

- **Todo**: Issue created, awaiting assignment
- **In Progress**: Cursor actively working on implementation
- **In Review**: Implementation complete, undergoing validation
- **Done**: Issue completed and verified

## 7. Success metrics

### 7.1 Integration metrics

- Task sync reliability (target: 99%+ successful syncs)
- Task completion accuracy (target: 95%+ correctly updated states)
- MCP server response time (target: < 2 seconds)
- Error recovery rate (target: 100% of failures recovered within 1 hour)

### 7.2 Development metrics

- Issue completion velocity (target: 3-4 issues per week)
- Phase milestone adherence (target: 90%+ milestones on schedule)
- Task estimation accuracy (target: 80%+ within estimate range)
- Cross-phase dependency management (target: 0 blocking dependencies)

## 8. Technical considerations

### 8.1 MCP Server Configuration

- Bot User: "Cursor" created in Linear with appropriate permissions
- API Key: Secure token management with rotation capability
- Rate Limiting: Respect Linear API limits with appropriate backoff
- Error Logging: Comprehensive logging for debugging and monitoring

### 8.2 Data Synchronization

- Real-time state updates between Cursor and Linear
- Conflict resolution for simultaneous updates
- Backup and recovery mechanisms for sync failures
- Audit trail for all task state changes

### 8.3 Security Considerations

- Secure API key storage and transmission
- Access controls for sensitive project information
- Audit logging for all API interactions
- Compliance with data protection requirements

## 9. Milestones & sequencing

### 9.1 Setup Phase (1 week)

- Configure Linear team and bot user
- Import all 40 issues into Linear
- Test MCP server integration
- Validate task sync functionality

### 9.2 Phase 1 Execution (2-3 months)

- Execute foundation issues CUR-1 through CUR-13
- Monitor integration performance
- Refine task estimation based on actual completion times
- Prepare for Phase 2 transition

### 9.3 Phase 2 & 3 Execution (4-6 months)

- Continue automated task management
- Scale integration for increased complexity
- Generate progress reports and metrics
- Plan transition to maintenance mode

## 10. User stories

### 10.1 Automated Task Fetching

- **ID**: LI-001
- **Description**: As a Cursor bot, I want to automatically fetch open tasks from Linear so that I can work on the highest priority items.
- **Acceptance Criteria**:
  - MCP server polls Linear API every 15 minutes
  - Tasks filtered by team and status
  - Priority-based task selection implemented
  - Error handling for API failures included

### 10.2 Task State Synchronization

- **ID**: LI-002
- **Description**: As a project manager, I want task states to sync automatically between Cursor and Linear so that I can track progress in real-time.
- **Acceptance Criteria**:
  - Task state changes reflected within 5 minutes
  - Bidirectional sync prevents conflicts
  - Audit trail maintained for all changes
  - Manual override capability available

### 10.3 Progress Reporting

- **ID**: LI-003
- **Description**: As a stakeholder, I want automated progress reports from Linear so that I can understand project velocity and blockers.
- **Acceptance Criteria**:
  - Weekly progress summaries generated
  - Milestone completion tracking included
  - Velocity metrics calculated automatically
  - Exception reports for blocked or overdue tasks
