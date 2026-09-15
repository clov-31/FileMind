# FileMind AI Context

## Current Goal
Build a conversational file-management agent.

## Current Phase
Phase 2 — Interactive Chat Agent (just starting).

## Architecture

```txt
CLI → Chat Loop → Tool Dispatcher → File Tools
                     ↓
                  Ollama (llama3.1:8b)
```

## Safety Invariants
- All filesystem ops pass validate_path()
- delete = quarantine, never permanent
- LLM cannot self-approve destructive actions
- dry-run by default
- every mutation is audited

## Source of Truth
- Current state: .context/current_state.md
- Tasks: .context/tasks/
- Decisions: .context/decisions/
- Active breadcrumb: .context/breadcrumbs/...
- Roadmap: docs/ROADMAP.md

## Current Task
TASK-0023 – Implement rename_file().