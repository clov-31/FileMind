# TASK-0021 — move_file

Status: DONE (conditional_pass)
Phase: 2
Completed: 2026-09-14
Owner: AI + Developer

## Requirement

Implement `move_file(src, dst)`.

## Constraints

- Both paths must pass `validate_path()`
- Never overwrite
- Collision → `(1)`, `(2)` suffix
- Audit before/after
- Support dry-run
- Phase 1 safety rules unchanged

## Acceptance Criteria

- [x] `move_file` works in sandbox
- [x] Collision handled
- [x] Audit log written
- [x] Tests pass — builder reported 18 focused tests + 50 full suite; evaluator test-quality assessment deferred
- [x] Breadcrumb updated

## Implementation Summary

- Added `agent/tools/move_file.py`
- Added `tests/test_move_file.py`
- Uses `validate_path()` for source, destination, and proposed destination
- Uses `AuditLog` for real execution
- Uses `resolve_collision()` from `organize_files`
- Dry-run is default
- Never overwrite via `os.link` + `os.unlink`
- Same-volume only; no cross-volume fallback

## Evaluation Summary

Evaluator: ChatGPT  
Session: `S-0021-EVAL-001`  
Verdict: `conditional_pass`

- Safety: pass
- Filesystem semantics: conditional
- Audit: pass
- Test assessment: pending Audit/Test phase

## Open Decisions

- Confirm whether `move_file` must support folders
- Confirm whether cross-volume move is required
- Clarify atomicity contract for `os.link` + `os.unlink`

## Result

Implemented and documented. Conditional pass because folder support and cross-volume semantics remain contract decisions, and filesystem atomicity semantics require clarification before claiming full transactional atomicity.

## Next

TASK-0022 — `delete_file()`