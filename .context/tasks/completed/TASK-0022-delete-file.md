
# TASK-0022 — delete_file()

**Status:** PLANNED  
**Phase:** 2  
**Depends on:** TASK-0021 (move_file, completed)  

---

## Requirement

Implement `delete_file(path)` that **never permanently deletes**.  
Instead, it moves the target into a quarantine folder.

### Signature

```python
def delete_file(path: str, *, dry_run: bool = True) -> DeleteResult
````

### Constraints

- Must call `validate_path(path)` before any filesystem operation.
- Must **NOT** use `os.remove`, `os.unlink`, or `shutil.rmtree` directly on user paths.
- Deletion = move to quarantine dir (default: `<repo>/.quarantine/`).
- Quarantine must preserve original filename + timestamp to avoid collision.
- Must support `dry_run` (default `True`).
- Must write audit log entry **BEFORE** and **AFTER** the operation.
- Must **NOT** follow symlinks outside the allowed root.
- Must refuse to quarantine:
    - paths outside allowed root
    - the quarantine dir itself
    - non-existent paths
    - directories (only files in this task; folder delete is out of scope)
- Must reuse `validate_path` from `agent/core/safety.py`.
- Must reuse audit logger from `agent/core/audit.py`.
- Must follow the structural pattern of `agent/tools/move_file.py`.

### Out of Scope

- Permanent delete
- Recursive folder delete
- Restore-from-quarantine (future task)
- Quarantine retention policy (future task)

## Acceptance Criteria

- [ ] `delete_file()` implemented in `agent/tools/delete_file.py`
- [ ] `dry_run=True` default; no filesystem mutation when True
- [ ] Quarantine path is created if missing
- [ ] Filename collision in quarantine resolved with timestamp suffix
- [ ] `validate_path` called on input
- [ ] Audit log written before and after
- [ ] Refuses non-existent path, out-of-root path, quarantine dir itself, and directories
- [ ] Unit tests in `tests/test_delete_file.py` covering:
    - happy path (file moved to quarantine)
    - dry_run (no mutation)
    - non-existent path
    - out-of-root path
    - directory input rejected
    - quarantine dir input rejected
    - collision handling
- [ ] All tests pass (`pytest`)
- [ ] No changes to Phase 1 files unless strictly required

## Edge Cases To Test

- File already inside quarantine → must be rejected.
- Two files with same name deleted in sequence → second gets timestamp suffix.
- Symlink pointing outside root → rejected by `validate_path`.
- `dry_run=True` → audit log written but no FS mutation.
- Path with trailing slash / mixed separators (Windows).
- Empty string path → rejected.

## Deliverables (Builder)

- `agent/tools/delete_file.py`
- `tests/test_delete_file.py`
- Updated `agent/tools/__init__.py` if needed
- Breadcrumb: `.context/breadcrumbs/2026-09-14-<HHMM>-delete-file.md`
- Updated `.context/current_state.md`
- Session note: `.context/sessions/S-022-ARC-001-DeepSeek.md`

## Template sessions note 

session_id: S-0022-BLD-001
task_id: TASK-0022

role: builder
phase: implementation

agent: <Codex | Claude Code | ...>
mode: ai-assisted

started_at: 2026-09-14

objective:
  Implement TASK-0022 delete_file() sesuai task file.

context:
  task_status: in_progress
  depends_on: TASK-0021 (move_file, completed)
  related_adr: ADR-003-quarantine-not-delete
  previous_session: S-0022-ARC-001

inputs:
  - AI_CONTEXT.md
  - AI_RULES.md
  - current_state.md
  - .context/tasks/active/TASK-0022-delete-file.md
  - .context/decisions/ADR-003-quarantine-not-delete.md
  - agent/core/safety.py
  - agent/core/audit.py
  - agent/tools/move_file.py
  - tests/test_move_file.py

actions:
  - <diisi Builder>

findings:
  - <diisi Builder>

decisions:
  - <diisi Builder, hanya jika ada deviasi dari task file>

outputs:
  - agent/tools/delete_file.py
  - tests/test_delete_file.py
  - .context/breadcrumbs/2026-09-14-<HHMM>-delete-file.md
  - Updated .context/current_state.md
  - Session note: .context/sessions/S-0022-BLD-001-<agent>.md

tests:
  command: pytest
  result: <diisi Builder>

next:
  - Evaluator session (S-0022-EVL-001)

notes:
  - <diisi Builder>