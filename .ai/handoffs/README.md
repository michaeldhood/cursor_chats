# Handoffs Directory

This directory contains handoff files that facilitate context transfer between AI assistant sessions or threads when working on specific tasks.

## Purpose

Handoff files ensure smooth continuity when:

- Switching between AI chat threads/sessions
- Ending a work session before task completion
- A significant sub-goal within a task is achieved and new context needs to be set
- Explicitly requested by the user

## File Naming Convention

- Format: `task{id}_handoff{iteration}.md`
- Examples: `task6_handoff1.md`, `task12_handoff2.md`
- First handoff can omit iteration: `task6_handoff.md`

## Content Structure

Each handoff file typically includes:

- Project context and current task information
- Current situation & key findings
- Immediate next actions & goals
- Key files and references
- Success criteria for next phase

## Usage

Handoff files complement the main Task Magic system by providing operational "state snapshots" for task-level continuity, while the main task files track overall lifecycle and the plan files describe feature requirements.

---

_Handoffs directory initialized: 2025-06-06T22:52:20Z_
