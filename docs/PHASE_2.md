# Phase 2 — Interactive Chat Agent: Requirements

> This is a requirements/scope brief, not a technical implementation plan.
> Claude Code should read this alongside CLAUDE.md and the actual Phase 1
> source code, then produce its own technical plan (via plan mode) the same
> way it did for Phase 1. This document doesn't invent file names or function
> signatures for the existing Phase 1 code — it hasn't seen what was actually
> built there.

---

> **Status per 10 September 2026 — konteks tambahan:**
>
> Dokumen ini adalah requirements murni. Untuk urutan build, deadline, dan
> deliverable tambahan, rujuk `docs/ROADMAP.md` bagian September.
> Ringkasnya:
>
> - **Urutan build tool (wajib):** `move_file` → `delete_file` (quarantine)
>   → `rename_file` → `create_folder`
> - **Deadline internal:** Claude Code tersedia sampai 9 September.
>   Prioritaskan build di Minggu 1–2; reverse-engineer & rebuild manual
>   dijadwalkan setelahnya (mandiri).
> - **Deliverable tambahan di luar dokumen ini:** testing manual 4 tool baru,
>   scaffold self-assessment Phase 2 (pola `docs/archive/AUDIT_REPORT.md` +
>   `docs/COMPONENT_CHECKLIST.md` Phase 1).
> - **Out of scope tetap sama** — routing (Phase 3), watchdog (Phase 4),
>   Office/Canva (Phase 5–6).

---
## Goal

Turn the Phase 1 CLI (`python -m agent scan --folder ... --execute`) into an
actual conversational agent: type a request in plain language, the agent
decides what to do and does it. A terminal interface that feels closer to
Claude Code than a bare REPL.

## New capabilities needed (beyond what Phase 1 built)

Phase 1 has exactly two operations: `scan_folder` (read-only) and
`organize_files` (batch auto-classify-and-move). Phase 2 needs individual,
on-request operations the model can call one at a time:

| Tool | What it does | Safety note |
|---|---|---|
| `move_file(src, dst)` | Move one file/folder to a specific destination | Same `validate_path` check on both src and dst; collision → `(1)`, `(2)` suffix, same as Phase 1 |
| `delete_file(path)` | "Delete" a file | **Always routes to `_Quarantine/`, never `os.remove()`** — safety rule 1 doesn't change just because the request came from chat instead of a CLI flag |
| `rename_file(path, new_name)` | Rename in place | Collision check at the new name |
| `create_folder(path)` (optionally `create_file(path)` for an empty file) | Make a new folder/file | Destination must resolve inside a whitelisted folder |

All four go through the exact same `validate_path` (whitelist + hard-block)
as Phase 1's tools, get logged to `actions.log` the same way, and the
batch-confirmation threshold still applies — "hapus semua screenshot tahun
lalu" can easily match dozens of files, and the model still can't
self-approve that.

`organize_files` and `scan_folder` don't go away — they become two more
entries in the same toolbox, callable by name ("rapihin Downloads dong")
instead of only via CLI flag.

## Chat loop

- Each turn: user message → sent to `llama3.1:8b` via Ollama with the tool
  definitions attached → model replies in plain text, or requests a tool
  call → dispatch to the real function → result fed back to the model →
  model gives a final natural-language reply.
- Conversation history kept in memory for the session.
- Reuse (and strengthen) the system-prompt instruction already in CLAUDE.md's
  Ollama Notes: only call a tool when the user is actually asking for an
  action. Matters more now — more tools exist for a small model to reach for
  unnecessarily.
- **Show the tool call itself in the interface**, not just the model's final
  summary — e.g. a status line like `→ moving laporan.pdf to Documents/`
  before the model's reply. This echoes how Claude Code works, and it's a
  safety feature: the user sees what happened, not just a claim about what
  happened.

## Terminal interface — "rapih dan interaktif"

Recommend **Rich** + **prompt_toolkit** — gets most of the "feels like Claude
Code" quality without adopting a full TUI framework:
- **Rich**: styled/colored output, panels, a live spinner while the model is
  thinking (genuinely useful — CPU-only inference isn't instant), optional
  markdown rendering of replies.
- **prompt_toolkit**: a proper input line with history (up-arrow to recall
  previous messages), instead of a bare `input()`.

Visually distinguish three things, not one undifferentiated stream of text:
user input, the assistant's reply, and tool-call status lines.

Bigger option, worth deferring: **Textual** (also Textualize) — a full TUI
with scrollable panes and mouse support. Genuinely nicer, meaningfully more
to build. Revisit once the simpler version works — same "decide the big UI
question later" logic already applied to Tauri vs. Electron in Phase 7.

## Decisions made (defaults chosen so this isn't blocked — flip any of these later)

- **Chat history**: session-only for now, nothing persisted across restarts.
  A saved session log is a small add later if wanted.
- **`create_file`**: empty file/folder only. Writing generated content into a
  new file leans into Office-helper territory — that's Phase 5, keeps this
  phase's scope from creeping.
- **Exit**: support both typing `exit`/`quit` and Ctrl+C.

Flag any of these to the user before building if they seem wrong; otherwise
proceed with them as stated.

## Explicitly out of scope for Phase 2

- Local/cloud routing (Phase 3)
- Background/automatic triggering — `watchdog` (Phase 4)
- Anything Word/Excel/Canva-specific (Phases 5–6)
