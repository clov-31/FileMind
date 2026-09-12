> Backup copy — reconstructed from chat history after the original Claude Code
> terminal session closed unexpectedly. Content is unmodified from the version
> reviewed and approved (pending two corrections noted separately).

# Phase 1 — CLI file organizer (scan → classify → propose → confirm → move)

## Context

The repo is a bare scaffold: `CLAUDE.md`, `env.example`, `.gitignore`, and nothing else. Phase 1 of the roadmap is the first working slice: scan one folder, classify what's in it, propose moves as a dry run, and execute only after explicit confirmation. Everything downstream (chat loop, routing, watchdog, Office helpers) sits on top of the safety and tool primitives built here, so this phase is really about getting the *guardrails* right — the classification is the easy part.

Two facts found while orienting that changed the plan:

- **`gemma4:e4b` is not installed and is not a real Ollama tag.** `ollama list` shows `llama3.1:8b`, `qwen2.5:3b`, `llama3.2:3b`, `phi3:mini`. Decision: default to **`llama3.1:8b`** (4.9 GB, tool-calling capable, 128k context, inside the 8–10 GB RAM budget). `phi3:mini` lacks the `tools` capability and is out of consideration entirely.
- **`C:\Users\mirza\Downloads` holds 151 top-level entries**, including real directories (`Apps`, `Ahok_HYB`) mixed in with files. That's the live test case, and it means directory handling can't be an afterthought.

Confirmed with the user: default model → `llama3.1:8b`; CLAUDE.md gets corrected (model tag, OS line, structure line); organized files land in **subfolders inside the watched folder**, not a separate root.

## Guiding decision: rules first, LLM second

The extension map is the **primary** classifier, not a fallback. It decides the category for the overwhelming majority of those 151 files deterministically. The LLM is consulted only for entries whose extension isn't in the map.

This matters for two reasons: Phase 1 works with Ollama down, and the entire scan → propose → confirm → move pipeline can be built and tested before any model is wired in. Build in that order.

## Files to create

```
agent/
  __init__.py
  __main__.py              # entry point: python -m agent
  core/
    config.py              # Config dataclass, loads .env via python-dotenv
    audit.py               # append-only JSONL audit log
    safety.py              # path validation, whitelist, hard-blocks
    classify.py            # extension map + LLM escalation for unknowns
    llm.py                 # Ollama chat client
    cli.py                 # Phase 1 flow + argparse
  tools/
    scan_folder.py
    organize_files.py
  prompts/
    system_prompt.md
    classify_files.md
  routing/
    __init__.py            # Phase 3 placeholder, empty for now
logs/.gitkeep
tests/
  test_safety.py
  test_scan_folder.py
  test_organize_files.py
  test_classify.py
requirements.txt
README.md
```

`env.example` stays at the repo root (already there); the CLAUDE.md structure block gets corrected to match rather than moving the file to `/config/`.

## Build order

### 1. `core/config.py`, `core/safety.py`, `core/audit.py` — the guardrails

`config.py`: dataclass loaded from `.env` via `python-dotenv`. Fields mirror `env.example`: `ollama_host`, `ollama_model`, `ollama_num_ctx`, `watched_folders: list[Path]`, `quarantine_folder`, `batch_confirm_threshold: int`, `log_path`. Fails loudly at startup if `WATCHED_FOLDERS` is empty or points at a nonexistent path. No hardcoded paths or model names anywhere else in the codebase — everything reads from here.

`safety.py` — one function, `validate_path(path, config) -> tuple[bool, str]`:
- Resolve to an absolute real path first (kills `..` traversal and symlink escapes).
- Hard-block check runs **before** the whitelist: `C:\Windows`, `C:\Program Files`, `C:\Program Files (x86)`, anything under `AppData`. A hard-blocked path is rejected even if someone lists it in `WATCHED_FOLDERS`.
- Whitelist check: path must be inside one of `watched_folders` (`Path.is_relative_to`).
- Returns a reason string on rejection so the CLI and the log can both explain the refusal.

`audit.py` — append-only JSONL to `LOG_PATH`, one object per line: `{ts, action, status, src, dst, tier, detail}`. Two-step by design, per safety rule 2: write `status: "planned"` **before** the move, then a follow-up `status: "ok"` or `status: "failed"` after. `tier` is `"local"`, `"cloud"`, or `"rule"` (for deterministic, no-model decisions). Creates `logs/` if missing.

### 2. `tools/scan_folder.py`

`scan_folder(folder: str, config: Config) -> dict` returning `{success, message, data}` like every tool.

Non-recursive — top level only for Phase 1. For each entry, record `name, path, ext, size_bytes, mtime, is_dir`.

Skips, each for a stated reason:
- **Directories** — reported in the summary as "N folders skipped" but never moved. Moving a folder tree on first run is a bad first impression.
- **Category destination folders** (`Documents/`, `Images/`, …) and `_Quarantine/` — this is what makes repeat runs idempotent. Without it, run two re-scans and re-files what run one just organized.
- **In-progress downloads**: `.crdownload`, `.part`, `.tmp`, `.partial`.
- Hidden/system files.

Calls `validate_path` on the target folder before reading anything.

### 3. `core/classify.py`

`CATEGORIES` → extension mapping:

| Category | Extensions |
|---|---|
| Documents | `.pdf .docx .doc .txt .md .rtf .odt .pptx .ppt` |
| Spreadsheets | `.xlsx .xls .csv` |
| Images | `.png .jpg .jpeg .gif .webp .svg .bmp .heic` |
| Video | `.mp4 .mkv .mov .avi .webm` |
| Audio | `.mp3 .wav .m4a .flac` |
| Installers | `.exe .msi` |
| Archives | `.zip .rar .7z .tar .gz` |
| Code | `.py .js .ts .json .html .css .ipynb` |
| Other | everything else → LLM escalation |

`classify(entries, config, use_llm=True)` returns per-file `(category, tier)` so the audit log records whether a rule or the model decided.

### 4. `tools/organize_files.py`

`organize_files(moves: list[Move], config: Config, dry_run: bool = True) -> dict`

`dry_run=True` is the **signature default**, per safety rule 3 — not merely a CLI preview step. The caller has to opt into touching disk.

- Re-validates every source and destination path through `safety.validate_path`. LLM-proposed arguments are never trusted; this is the last line of defence.
- **Collision handling:** never overwrite. If the destination exists, append ` (1)`, ` (2)`, … Windows-style.
- **Per-file error isolation:** on Windows the practical "is this file open?" check is attempting the move and catching the sharing violation — a pre-check races anyway. So each move is individually wrapped; a locked or vanished file is logged `status: "failed"` with the error and the batch continues. One bad file must never abort the other 150.
- Uses `shutil.move` (handles cross-volume; here it's same-volume renames).
- Returns per-file outcomes so the CLI can print a real summary: N moved, N failed, N skipped.

### 5. `core/cli.py` + `__main__.py`

```
python -m agent scan                       # dry run, uses first WATCHED_FOLDER
python -m agent scan --folder "<path>"     # dry run, explicit folder
python -m agent scan --execute             # propose, then ask, then move
python -m agent scan --no-llm              # rules only, skip Ollama entirely
```

Flow: scan → classify → build move list → print a grouped table (category, count, sample filenames) → if `--execute`, and the move count exceeds `BATCH_CONFIRM_THRESHOLD` (5), require a typed `yes` (safety rule 6 — the model cannot self-approve; with 151 files this always triggers) → execute → print summary and the log path.

Default with no `--execute` is dry run. Nothing touches disk unless the user asks twice.

### 6. `core/llm.py` + prompts

Thin Ollama client over `POST /api/chat` (`requests`), `stream=False`, `format: "json"`, and **`options: {"num_ctx": 8192}` set explicitly** — Ollama silently defaults to 4K regardless of the model's real maximum, which would truncate schemas and history without any error.

- Batches ~25 unknown files per call to stay inside context.
- **Validates every response**: parse JSON, drop any filename the model returns that wasn't in the batch it was given (hallucination guard), reject categories outside the enum, and fall back to `Other` for anything malformed. Never raises into the agent loop.
- Ollama unreachable → warn once, classify rules-only, keep going. A down model degrades the result; it doesn't break the run.

`prompts/system_prompt.md` includes the explicit instruction from CLAUDE.md's Ollama notes: only call a tool when the user asks for an action, answer plain questions in plain text — small local models over-trigger tool calls badly. `prompts/classify_files.md` is the Phase 1 classification prompt with the category enum and a strict-JSON output contract.

### 7. `requirements.txt`, `README.md`, CLAUDE.md corrections

Dependencies for this phase only: `python-dotenv`, `requests`, `pytest`. `watchdog`, `python-docx`, `openpyxl`, `anthropic` belong to later phases and are not installed yet.

CLAUDE.md edits (user-approved):
- Default model line → `llama3.1:8b`, noting it was verified against `ollama list`.
- OS line → confirmed Windows 11 (verified this session), drop the "assumed" hedge.
- Repository-structure block → `env.example` at root, not `/config/.env.example`.
- Roadmap → tick Phase 1.

## Verification

1. **Unit tests** — `pytest tests/`, all using `tmp_path` so no real user files are involved:
   - `test_safety.py`: hard-blocked paths rejected even when whitelisted; `..` traversal rejected; path outside `WATCHED_FOLDERS` rejected; valid path accepted.
   - `test_scan_folder.py`: directories skipped; category folders skipped; `.crdownload` skipped.
   - `test_organize_files.py`: `dry_run=True` moves nothing; collision produces ` (1)` rather than overwriting; a locked/unreadable file fails alone while the rest of the batch succeeds.
   - `test_classify.py`: extension map correctness; malformed LLM JSON degrades to `Other` instead of raising.
2. **Dry run against the real folder** — `python -m agent scan --folder "C:\Users\mirza\Downloads"`. Expect ~151 entries, folders reported as skipped, a sensible category breakdown, and **zero disk changes** (confirm with `git status` and by eyeballing Downloads).
3. **Execute against a sandbox first** — copy ~20 files from Downloads into a scratch folder, point `WATCHED_FOLDERS` at it, run `--execute`, confirm the moves landed and `logs/actions.log` has a `planned` + `ok` pair per file.
4. **Idempotency** — re-run the scan on the sandbox. Must propose **0 moves**; if it re-files its own output, the destination-folder exclusion in step 2 is broken.
5. **Ollama-down path** — stop Ollama (or run `--no-llm`) and confirm the scan still completes on rules alone with a single warning.
6. Only after 2–5 pass on the sandbox, run `--execute` against real Downloads.
