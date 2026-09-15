```markdown
# TASK-0023 — rename_file()

**Status:** PASSED — S-0023-EVL-002 (second pass)
**Phase:** 2
**Depends on:** TASK-0021 (move_file, conditional_pass), TASK-0022 (delete_file, conditional_pass)

---

## Requirement

Implement `rename_file(path, new_name)` that renames a file **in place**
(same parent directory) without overwriting any existing file.

Rename is **not** a delete and **not** a move across directories.
Cross-directory relocation must be delegated to `move_file()`.

### Signature

```python
def rename_file(path: str, new_name: str, *, dry_run: bool = True) -> RenameResult
```

### Constraints

- Must call `validate_path(path)` before any filesystem operation.
- Must validate that `new_name` is a **bare filename**, not a path.
  - Reject if `new_name` contains `/`, `\`, `..`, or resolves outside the
    parent directory of `path`.
- Must **NOT** use `os.rename`, `os.replace`, or `shutil.move` directly on
  user paths without going through the safety layer.
- Must **NOT** overwrite an existing target file.
  - If target exists, resolve collision with suffix: `name (1).ext`,
    `name (2).ext`, dst — consistent with `move_file()`.
- Must support `dry_run` (default `True`).
- Must write audit log entry **BEFORE** and **AFTER** the operation.
- Must **NOT** follow symlinks outside the allowed root.
- Must refuse to rename when:
    - `path` is outside allowed root
    - `path` does not exist
    - `path` is a directory (file-only scope)
    - `path` is inside the quarantine dir
    - `path` is a symlink pointing outside root
    - `new_name` is empty, contains separators, or is `..` / `.`
    - `path` and `new_name` resolve to the same path (no-op refusal)
- Must reuse `validate_path` from `agent/core/safety.py`.
- Must reuse audit logger from `agent/core/audit.py`.
- Must follow the structural pattern of `agent/tools/move_file.py`
  and `agent/tools/delete_file.py`.
- Case-only rename on case-insensitive filesystems (Windows) must be
  supported via a temporary intermediate name to avoid false "already exists".

### Out of Scope

- Cross-directory rename (delegate to `move_file()`).
- Folder rename.
- Overwrite-and-replace semantics (future ADR if needed).
- Batch rename.
- Regex / pattern-based rename.

## Acceptance Criteria

- [x] `rename_file()` implemented in `agent/tools/rename_file.py`
- [x] `dry_run=True` default; no filesystem mutation when True
- [x] `validate_path` called on `path`
- [x] `new_name` validated as bare filename (no separators, no `..`)
- [x] Refuses: non-existent path, out-of-root, directory, quarantine dir,
      symlink-out-of-root, empty/invalid `new_name`, `src == dst`
- [x] Collision handling: target exists → suffix `(1)`, `(2)`, dst, no overwrite
- [x] Case-only rename works on Windows
- [x] Audit log written before and after
- [x] Unit tests in `tests/test_rename_file.py` covering:
    - happy path (file renamed in place)
    - dry_run (no mutation, no FS side effect except documented)
    - non-existent path
    - out-of-root path
    - directory input rejected
    - quarantine dir input rejected
    - `new_name` with `/` rejected
    - `new_name` with `..` rejected
    - empty `new_name` rejected
    - `src == dst` rejected
    - collision handling (forced collision, not vacuous)
    - symlink-out-of-root rejected (skipif Windows without symlink privilege)
    - case-only rename (skipif non-Windows)
- [x] All tests pass (`pytest`) — reported by human, not independently
      verified
- [x] No changes to Phase 1 files unless strictly required
- [x] `agent/tools/__init__.py` updated if needed

> ☑ checklist marked by builder, pending S-0023-EVL-002 verification.

## Edge Cases To Test

- Rename `a.txt` → `a.txt` (same path) → rejected.
- Rename `a.txt` → `A.txt` on Windows → allowed via temp name.
- Rename `a.txt` → `b.txt` when `b.txt` exists → becomes `b (1).txt`.
- Rename `a.txt` → `sub/b.txt` → rejected (`/` in new_name).
- Rename `a.txt` → `..` → rejected.
- Rename `a.txt` → `` (empty) → rejected.
- Rename symlink inside sandbox pointing outside root → rejected.
- `dry_run=True` → audit reflects dry-run, no mutation.
- Path with trailing slash / mixed separators (Windows) → treated as file
  path, not directory.
- Empty string path → rejected via `validate_path`.

## Lessons From TASK-0022 (must address)

- **F-1 pattern:** Include symlink-out-of-root test explicitly (skipif Windows
  without symlink privilege). Do not defer to future task. ✅ Addressed —
  `test_symlink_pointing_outside_root_is_refused`.
- **F-2 pattern:** Collision test must **force** collision via monkeypatched
  deterministic timestamp OR by pre-creating the exact candidate name.
  Do not write vacuous assertions. ✅ Addressed —
  `test_collision_forced_by_precreating_exact_candidate`,
  `test_double_collision_uses_second_suffix`,
  `test_collision_race_retries_next_suffix_without_overwriting`.
- **F-3 pattern:** Document dry-run side-effect contract explicitly in the
  session note and `current_state.md`. Decide: does `dry_run=True` touch the
  filesystem at all (e.g., audit parent mkdir)? State it. Pin it with a test.
  ✅ Resolved — ADR-001 authoritative: dry-run writes audit and may mkdir
  parent. Pinned by `test_dry_run_writes_audit_per_adr_001`.
- **F-4 pattern:** If any infrastructure directory must be created, either
  log `planned` before creation, or document that infra-dir creation is
  outside the audited operation. State which and pin with a test.
  ✅ Addressed — audit directory creation documented as ADR-001 sanctioned;
  `test_no_infra_dir_created_by_real_rename` pins no other infra dirs.
- **F-5 pattern:** If `new_name` or target path is exempt from
  `validate_path` (e.g., target is the new name, not the input), document
  the exemption in `current_state.md` Open Decisions.
  ✅ Documented — `new_name` is a bare filename, not a path;
  `dst = parent / new_name` is still passed to `validate_path(must_exist=False)`.

## Deliverables (Builder)

- `agent/tools/rename_file.py` ✅
- `tests/test_rename_file.py` ✅
- Updated `agent/tools/__init__.py` ✅
- Breadcrumb: `.context/breadcrumbs/2026-09-15-<HHMM>-rename-file.md` ✅
- Updated `.context/current_state.md` ✅
- Session note: `.context/sessions/S-0023-BLD-001-Cursor.md` ✅
- Follow-up session note: `.context/sessions/S-0023-BLD-002-DeepSeek.md` ✅

---

## Evaluation (S-0023-EVL-001)

**Verdict:** fail

**Blocking:**
1. `agent/tools/__init__.py` imports `scan_folder` from `agent.tools.rename_file`, breaking pytest collection.
2. `src == dst` is not refused; returns `success=True`, `status="skipped"`.
3. Dry-run audit directory contract is inconsistent: implementation creates audit dir, test expects no audit dir.

**Advisory:**
- POSIX case-only rename uses Windows temp path.
- Symlink inside root renames target, not link.

**Next:** S-0023-BLD-002 — Builder follow-up to fix blocking issues, then re-run pytest.

---

## Follow-up (S-0023-BLD-002)

**Agent:** DeepSeek (free plan)

**Actions:**
1. `agent/tools/__init__.py` — removed all re-exports. First attempt
   used per-module re-exports, which introduced attribute shadowing
   and broke 6 tests across the suite. Final file contains only a
   docstring.
2. `agent/tools/rename_file.py` — no-op branch now returns
   `success=False`, `status="skipped"`, detail
   `"Source already has that name: …"`.
3. `tests/test_rename_file.py` — `test_same_name_is_refused_as_noop`
   now asserts refusal; `test_dry_run_does_not_create_audit_directory`
   replaced by `test_dry_run_writes_audit_per_adr_001` per ADR-001.
4. `.context/current_state.md` — F-3 pinned to ADR-001; no-op pinned as
   refusal; `__init__.py` no-re-export decision documented.

**Result:** Human-run pytest reported green.

**Pending:** S-0023-EVL-002 — independent second-pass re-evaluation.

---

## Evaluation (S-0023-EVL-002)

**Verdict:** pass

**Prior findings resolution:**
- F-1 (__init__.py stale `scan_folder` import) — CLOSED. `__init__.py`
  now docstring-only; shadowing resolved; 0 collection errors.
- F-2 (`src == dst` not refused) — CLOSED. Returns `success=False`,
  `status="skipped"`; test asserts `is False`.
- F-3 (dry-run audit contract mismatch) — CLOSED. Old test removed;
  `test_dry_run_writes_audit_per_adr_001` pins ADR-001.

**Blocking:** none.

**Advisory (deferred, non-blocking):**
- F-4 POSIX case-only rename routes through Windows temp path.
- F-5 Symlink-in-root comment/behavior mismatch.
- F-6 Case-only second stage uses raw `os.link`/`os.unlink` instead of
  `_move_without_overwrite`.

**Regression:** human-run pytest reported 91 passed, 2 skipped, 0
failed. Not independently verified.

**Next:** Task closed — proceed to S-0023-TST-001.