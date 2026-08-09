# CLAUDE.md

This file is the project brief for Claude Code. Read it fully before writing or changing any code — especially the safety rules section, which is non-negotiable.

## Project Overview

A local-first personal AI agent, running primarily on-device via Ollama, with two responsibilities:

1. **File Manager** — scans/watches specific folders (Downloads, Desktop, etc.), classifies clutter, and organizes it into a sensible structure. Never deletes anything permanently.
2. **Productivity Assistant** — a chat interface that helps with everyday Word, Excel, and (later) Canva tasks.

Inspiration: JARVIS, scoped down to what a CPU-only laptop can realistically run, with an optional escalation path to the Claude API for anything the local model can't handle reliably.

## Owner's Hardware (hard constraint — do not assume more than this)

- Laptop: Lenovo IdeaPad Slim 3 14IAH8
- CPU: Intel Core i5-12450H (4P+8E cores, 12 threads) — **no discrete GPU**. All local inference is CPU-only.
- RAM: 16 GB total, ~15.7 GB usable. Budget max ~8–10 GB for the local model; the rest has to cover the OS, browser, editor, and Ollama's own overhead.
- OS: Windows (assumed — correct this line once confirmed)
- Storage: ~475 GB SSD — not a constraint

Local models must stay Q4-quantized, roughly 2B–12B parameters. Bigger risks running out of RAM or feeling too slow to be conversational.

## Architecture

Three layers:

1. **Brain** — reasoning engine, two tiers:
   - *Local (default):* small model served by Ollama at `localhost:11434` (OpenAI-compatible API). Handles file classification, routine chat, straightforward tool calls.
   - *Cloud (fallback):* Claude API. Reserved for cases the local model can't handle well — see routing rules below.
2. **Hands** — Python functions ("tools") that actually touch the filesystem/apps. The LLM never touches disk directly; it can only request a tool call, and the code decides whether to run it.
3. **Mouth** — the chat interface. CLI first; a small desktop window comes later.

## Hybrid Routing: Local vs. Cloud

Default to local. Escalate to the Claude API when:
- The local model's tool-call output fails validation twice in a row
- The task is an ambiguous, multi-step reorganization (not a simple filing rule)
- The user explicitly asks for the stronger model
- (Later, once we have logs to tune this) the local model's own confidence signal is low

Routine, repetitive operations should never need to leave the machine — that's the whole point of going local first.

## Tech Stack

- Python 3.11+
- Ollama for local inference
- Default local model: **`gemma4:e4b`** (~5 GB RAM) — solid tool-calling support, safe headroom while developing. Upgrade path: `gemma4:12b` (~8 GB RAM) once the pipeline is stable and it's not running alongside a lot of other memory-hungry apps.
- Claude API (`anthropic` SDK) for the cloud fallback tier
- `watchdog` for folder monitoring
- `python-docx`, `openpyxl` for reading/writing Office files directly (no need to have Word/Excel open)
- `pywin32` only if we later need to drive an already-open Word/Excel window via COM — avoid unless genuinely needed, it's Windows-only and heavier
- Desktop shell (Tauri vs. Electron): decide after the CLI + tool-calling loop works, not before

## Ollama Notes (read before wiring up the client)

- Ollama defaults to a 4K context window regardless of the model's real maximum — explicitly set `num_ctx` (8192+) on API calls, or tool schemas plus chat history will get silently truncated.
- Small local models tend to over-trigger tool calls, even on plain conversational input like "berapa 2+2?". The system prompt needs an explicit instruction: only call a tool when the user is asking for an action; answer questions in plain text. Goes into `prompts/system_prompt.md` — next step.
- Run `ollama list` / `ollama show <model>` after pulling to confirm the exact tag before putting it in `.env` — tags shift as new versions ship.

## Repository Structure (target)

```
/agent
  core/         # main loop — reads user input, calls the LLM, dispatches tool calls
  tools/        # one file per tool (organize_files.py, read_docx.py, ...)
  routing/      # local-vs-cloud decision logic
  prompts/      # system prompt(s), versioned
/config
  .env.example
/logs
  actions.log   # audit trail — every file operation, timestamped
/tests
CLAUDE.md
README.md
```

## Safety Rules for File Operations (non-negotiable)

1. **No permanent deletion.** "Delete" always means "move to `_Quarantine/` with a timestamp," never `os.remove()`. The user empties Quarantine manually, on their own schedule.
2. **Log every action** to `logs/actions.log` before executing: timestamp, action, source path, destination path, which tier (local/cloud) made the call.
3. **New tools default to `dry_run=True`** — return what *would* happen without doing it — until the logic has been manually verified.
4. **Whitelist, not blacklist.** The agent may only touch folders explicitly listed in `WATCHED_FOLDERS`. Never assume access to the whole filesystem.
5. **Hard-block system paths** regardless of whitelist: `C:\Windows`, `C:\Program Files`, `C:\Program Files (x86)`, anything under `AppData` unless explicitly added.
6. **Batch actions need confirmation.** Moving/renaming more than `BATCH_CONFIRM_THRESHOLD` files in one go requires an explicit yes from the user in chat — the LLM cannot self-approve bulk actions.
7. **Validate before executing.** Don't trust the LLM's tool-call arguments blindly — confirm the path exists, sits inside an allowed folder, and isn't currently open, before running anything.

## Coding Conventions

- Type hints on every function signature.
- Every tool function needs a clear docstring — it doubles as the tool description the LLM sees, so write it for the model's benefit, not just for humans reading the code.
- Tool functions return a structured result (`{success, message, data}`); never let a tool raise an uncaught exception back into the agent loop.
- No hardcoded paths, API keys, or model names — everything goes through `.env`.
- Keep individual tools small and single-purpose; compose behavior in `core/`, not inside the tools themselves.

## Roadmap

- [ ] Phase 1 — CLI: scan one folder, classify with the local model, propose moves (dry-run), execute on confirm
- [ ] Phase 2 — Wrap into a chat loop with tool-calling
- [ ] Phase 3 — Add the local/cloud routing layer
- [ ] Phase 4 — `watchdog` background monitoring of watched folders
- [ ] Phase 5 — Office helpers (`python-docx`, `openpyxl`)
- [ ] Phase 6 — Canva Connect API integration
- [ ] Phase 7 — Desktop shell / system tray presence

## Open Decisions

- OS confirmation (assumed Windows — correct this line if wrong)
- Exact model tag once pulled and verified with `ollama list`
- Desktop framework — revisit after Phase 2
