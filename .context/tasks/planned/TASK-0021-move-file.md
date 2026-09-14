# TASK-0021 — move_file

Status: PLANNED
Phase: 2
Estimated: 60 min

## Requirement
Implement move_file(src, dst).

## Constraints
- Both paths must pass validate_path()
- Never overwrite
- Collision → (1), (2) suffix
- Audit before/after
- Support dry-run
- Phase 1 safety rules unchanged

## Acceptance Criteria
- [ ] move_file works in sandbox
- [ ] Collision handled
- [ ] Audit log written
- [ ] Tests pass
- [ ] Breadcrumb updated