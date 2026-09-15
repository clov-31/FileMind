# S-0023-BLD-002 — Builder follow-up — rename_file()

- **Agent:** DeepSeek (free plan)
- **Role:** builder
- **Task:** TASK-0023 — rename_file()
- **Predecessor:** S-0023-EVL-001 (verdict: fail)
- **Successor:** S-0023-EVL-002
- **Status:** closed — fixes applied, human-run pytest reported green.

## Scope

Fix the three blocking findings from S-0023-EVL-001 plus two follow-up
collection/shadowing failures discovered on the first post-build pytest
run. No redesign.

## Changes

1. `agent/tools/__init__.py`
   - First attempt: per-module re-exports. This introduced attribute
     shadowing — the function `rename_file` bound to
     `agent.tools.rename_file` shadowed the submodule, breaking
     `monkeypatch.setattr("agent.tools.rename_file.<X>", …)`.
   - Final: file reduced to a docstring only. No imports, no `__all__`.
     Callers import directly from submodules
     (`from agent.tools.rename_file import rename_file`), which is
     already the pattern used throughout the test suite.
   - Resolves the 6 shadowing failures across test_delete_file.py,
     test_move_file.py, and test_rename_file.py.

2. `agent/tools/rename_file.py`
   - No-op branch (`source.name == new_name`) now returns
     `success=False`, `status="skipped"`, message
     `"Rename refused: Source already has that name: …"`.
   - Audit for the no-op branch emitted only when `dry_run=False`,
     matching the existing refusal pattern.
   - No other behavioral change.

3. `tests/test_rename_file.py`
   - `test_same_name_is_refused_as_noop`: asserts `success is False`,
     `status == "skipped"`, detail contains `"already"`.
   - `test_dry_run_does_not_create_audit_directory` →
     `test_dry_run_writes_audit_per_adr_001`: asserts ADR-001 contract —
     audit dir created, entries `planned` then `ok` with
     `detail == "dry_run"`, source unchanged, destination absent.
   - All other tests unchanged.

4. `.context/current_state.md`
   - Pinned F-3 to ADR-001 (dry-run writes audit; AuditLog may mkdir
     parent).
   - Pinned no-op as refusal (diverges from move/delete no-op-success).
   - F-4 / F-5 marked advisory, deferred.

## Not changed

- `agent/core/safety.py`, `agent/core/audit.py` — untouched.
- Signatures of `move_file()`, `delete_file()` — untouched.
- No new dependencies.
- POSIX case-only path (F-4) left as-is.
- Symlink-in-root semantics (F-5) left as-is.

## Verification

- **NOT RUN by builder.** Builder is stateless and cannot execute pytest.
- Human-led verification: two pytest runs were provided to the builder
  across this session. The first showed 8 failed / 83 passed / 2 skipped
  (collection had previously been blocked by the `__init__.py` import).
  After both fixes (shadowing + no-op), human reported the suite green.
- Builder does not assert pass independently.

## Handoff

- Next: S-0023-EVL-002 (evaluator, DeepSeek).