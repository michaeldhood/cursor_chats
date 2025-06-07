# Projects Directory

This directory contains individual project workspaces in the Task Magic system. Each project operates independently with its own tasks, plans, and context while sharing global memory for cross-project learning.

## Project Structure

Each project follows this standardized structure:

```
{project-name}/
  plan.md         # Primary project PRD
  TASKS.md        # Project-specific task checklist
  PROJECT.md      # Project metadata and overview
  tasks/          # Active task files
    task{id}_name.md
  context/        # Additional project documentation
    background.md
    {feature}-plan.md
    decisions.md
    investigation.md
```

## Creating Projects

To create a new project:

1. Ask your AI assistant to create a project using Task Magic
2. Provide a descriptive kebab-case name (e.g., `user-authentication`, `data-pipeline`)
3. The system will create the full structure and register it in `.ai/INDEX.md`

## Project Lifecycle

- **Active**: Currently being worked on
- **Completed**: Achieved deliverables and stable
- **Paused**: Temporarily halted but may resume
- **Archived**: No longer relevant or superseded

## Navigation

- Check `.ai/INDEX.md` for the global project registry
- Use Task Magic commands to switch between projects
- Reference other projects by name when needed

---

_Projects directory initialized: 2025-06-06T22:52:20Z_
