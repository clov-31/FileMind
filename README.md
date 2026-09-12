# file_mind

A local-first personal agent that organizes folders and (later) helps with Word
and Excel. Runs on Ollama on-device; the Claude API is a fallback tier, not the
default. See [CLAUDE.md](CLAUDE.md) for the full brief and the safety rules.

**Phase 1 is done:** scan a folder, classify what's in it, preview the moves,
execute only on confirmation.

## Problem

FileMind membantu merapikan file lokal dengan pendekatan local-first berbasis Ollama, tanpa penghapusan permanen dan dengan guardrail filesystem yang ketat.

## Cara menjalankan

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
cp env.example .env
python -m agent scan
```

## Struktur repo

Kode utama ada di `agent/`, pengujian di `tests/`, dan dokumentasi proyek ada di `docs/` serta `docs/archive/`.

## Status

Phase 1 selesai; Phase 2 sedang berjalan.

## Setup

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
cp env.example .env        # then edit .env — WATCHED_FOLDERS is required
```

`.env` is gitignored. `WATCHED_FOLDERS` is the whitelist: the agent cannot touch
anything outside it.

## Usage

```bash
# Preview. Never touches disk. This is the default.
python -m agent scan
python -m agent scan --folder "C:\Users\you\Downloads"

# Skip the local model; classify by extension rules only (much faster)
python -m agent scan --no-llm

# Actually move files — prompts for confirmation above BATCH_CONFIRM_THRESHOLD
python -m agent scan --execute
```

Files move into category subfolders **inside** the folder being scanned:
`Downloads/Documents/`, `Downloads/Images/`, and so on.

## How classification works

Extension rules decide the category for almost everything, deterministically and
instantly. Only files with an unrecognised extension go to the local model, in
validated batches — the model's answers are checked against the filenames it was
actually given before they can move anything.

This means the organizer works fine with Ollama stopped: unknown files just land
in `Other/` instead of being guessed at.

## What it will not do

- **Delete anything.** Ever. Not implemented, by design.
- **Overwrite anything.** A name collision becomes `report (1).pdf`.
- **Touch anything outside `WATCHED_FOLDERS`**, or `C:\Windows`, `Program Files`,
  or `AppData` — the last of which needs an explicit opt-in via `WATCHED_FOLDERS`.
- **Move folders.** Phase 1 only touches loose files at the top level.
- **Move in-progress downloads** (`.crdownload`, `.part`, `.tmp`).
- **Bulk-move without asking.** Above `BATCH_CONFIRM_THRESHOLD` files you type
  `yes` or nothing happens.

Every executed move is written to `logs/actions.log` as JSON lines — the intent
is logged *before* the move is attempted, so an interrupted run still leaves a
record of what was in flight.

## Tests

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

All tests run inside `tmp_path`; none touch real files.
