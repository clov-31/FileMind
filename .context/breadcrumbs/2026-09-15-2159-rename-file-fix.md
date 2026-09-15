# 2026-09-15-2159 — rename_file fix (S-0023-BLD-002)

## What
- Fixed `agent/tools/__init__.py` stale `rename_file` imports that broke
  pytest collection (3 errors).
- Changed `rename_file()` no-op (`src == dst`) from success/skipped to
  refusal/skipped per TASK-0023 / ADR-001.
- Updated `.context/current_state.md` F-3 and no-op decisions to pin to
  ADR-001.
- Updated `tests/test_rename_file.py`:
  - `test_same_name_is_refused_as_noop` now asserts refusal.
  - `test_dry_run_does_not_create_audit_directory` replaced with
    `test_dry_run_writes_audit_per_adr_001`.

## Why
- Blocking findings F-1, F-2, F-3 in S-0023-EVL-001.

## Open
- None blocking. F-4 (POSIX case-only) advisory, deferred.

## Next
- Human runs `pytest -v`.
- Then S-0023-EVL-002.