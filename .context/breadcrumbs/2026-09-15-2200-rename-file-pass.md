# 2026-09-15-2200 — rename_file pass (post S-0023-BLD-002)

## What
- `agent/tools/__init__.py` emptied of re-exports. Root cause was
  attribute shadowing: `from agent.tools.rename_file import rename_file`
  inside the package `__init__` bound the *function* `rename_file` to the
  attribute `agent.tools.rename_file`, shadowing the submodule. That broke
  every `monkeypatch.setattr("agent.tools.<mod>.<X>", …)` in the suite.
- `agent/tools/rename_file.py` no-op branch (`source.name == new_name`)
  now returns `success=False`, `status="skipped"`, detail
  `"Source already has that name: …"` per TASK-0023 / ADR-001.
- `tests/test_rename_file.py`:
  - `test_same_name_is_refused_as_noop` asserts refusal.
  - `test_dry_run_does_not_create_audit_directory` replaced with
    `test_dry_run_writes_audit_per_adr_001` per ADR-001.

## Why
- Blocking findings F-1, F-2, F-3 from S-0023-EVL-001.
- Follow-up collection errors and shadowing failures discovered on
  the first post-build pytest run.

## Result
- Human-run pytest reported green after both fixes applied.
- Suite: 93 tests, previously 8 failed / 83 passed / 2 skipped → now
  reported passing by human.

## Open
- F-4 (POSIX case-only rename uses Windows temp path) — advisory.
- F-5 (symlink inside root renames target, not link) — advisory.
- Neither blocks; both deferred to a follow-up if desired.

## Next
- S-0023-EVL-002 (evaluator, DeepSeek) — independent re-evaluation.
- If pass → S-0023-TST-001.