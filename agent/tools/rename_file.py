"""Safely rename one approved regular file in place (same parent directory).

This Phase 2 tool renames a single regular file without ever overwriting an
existing target and without crossing directories. Cross-directory relocation
belongs to ``move_file()``; deletion belongs to ``delete_file()``. A dry run is
the default, and real execution claims the new name atomically via ``os.link``
before removing the old one, so a racing process can never lose data.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from agent.core.audit import AuditLog, Tier
from agent.core.config import REPO_ROOT, Config
from agent.core.safety import validate_path
from agent.tools.organize_files import resolve_collision

ACTION = "rename"
_MAX_COLLISION_RETRIES = 100

_INVALID_NAME_CHARS = ("/", "\\")


def _result(
    success: bool,
    message: str,
    *,
    dry_run: bool,
    source: Path | str | None,
    destination: Path | str | None,
    status: str,
    detail: str | None = None,
) -> dict[str, Any]:
    """Build the standard result shape used by this single-file tool."""
    return {
        "success": success,
        "message": message,
        "data": {
            "dry_run": dry_run,
            "source": str(source) if source is not None else None,
            "destination": str(destination) if destination is not None else None,
            "status": status,
            "detail": detail,
        },
    }


def _detail(exc: OSError) -> str:
    """Format an expected filesystem error for a user-facing result and audit."""
    return f"{type(exc).__name__}: {exc}"


def _is_within(child: Path, parent: Path) -> bool:
    """True if ``child`` is ``parent`` or sits underneath it."""
    try:
        return child == parent or child.is_relative_to(parent)
    except (OSError, ValueError):
        return False


def _quarantine_dir(config: Config) -> Path:
    """Resolve the quarantine directory for this configuration."""
    if config.quarantine_folder is not None:
        return config.quarantine_folder.expanduser().resolve()
    return (REPO_ROOT / ".quarantine").resolve()


def _validate_new_name(new_name: str) -> str | None:
    """Return a refusal reason if ``new_name`` is not a bare filename, else None.

    Bare filename means: non-empty after strip, not ``.`` / ``..``, no path
    separators, and no literal ``..`` substring anywhere (ADR-004 decision,
    rejecting even harmless cases like ``foo..bar.txt``).
    """
    if not isinstance(new_name, str):
        return "new_name must be a string."
    stripped = new_name.strip()
    if stripped == "":
        return "new_name is empty after stripping whitespace."
    if stripped == "." or stripped == "..":
        return f"new_name '{stripped}' is not a valid filename."
    for ch in _INVALID_NAME_CHARS:
        if ch in new_name:
            return f"new_name must be a bare filename (contains '{ch}')."
    if ".." in new_name:
        return "new_name must not contain '..'."
    return None


def _move_without_overwrite(source: Path, destination: Path) -> None:
    """Move one same-volume file without ever replacing an existing target.

    Hard link claims the new name atomically; unlinking the source completes the
    rename. If the unlink fails, the just-created destination link is removed to
    restore the pre-operation namespace. Cross-volume is intentionally not
    supported for rename (same parent directory, so same volume).
    """
    os.link(source, destination)
    try:
        os.unlink(source)
    except OSError:
        try:
            os.unlink(destination)
        except OSError:
            pass
        raise


def _is_case_only_rename(source: Path, new_name: str) -> bool:
    """True if the rename differs only in case of the filename (same parent)."""
    return source.name != new_name and source.name.lower() == new_name.lower()


def rename_file(
    path: Path | str,
    new_name: str,
    config: Config,
    *,
    dry_run: bool = True,
    audit: AuditLog | None = None,
    tier: Tier = "local",
) -> dict[str, Any]:
    """Rename one approved regular file in place without overwriting.

    ``new_name`` is a bare filename, not a path. Cross-directory relocation is
    refused by design (delegate to ``move_file()``). With the default
    ``dry_run=True``, no user filesystem mutation occurs and no audit directory
    is created unless the caller passes an ``audit`` instance; a refusal is
    audit-logged only when ``dry_run=False``, matching ``move_file()`` and
    ``delete_file()``.
    """
    try:
        path_input = Path(path).expanduser()
    except (OSError, TypeError, ValueError) as exc:
        detail = f"Invalid path argument: {type(exc).__name__}: {exc}"
        if not dry_run:
            log = audit if audit is not None else AuditLog(config.log_path)
            log.record(
                ACTION, "skipped", src=str(path), dst=None, tier=tier, detail=detail
            )
        return _result(
            False,
            f"Rename skipped: {detail}",
            dry_run=dry_run,
            source=None,
            destination=None,
            status="skipped",
            detail=detail,
        )

    quarantine = _quarantine_dir(config)

    def skipped(reason: str, source: Path | None, destination: Path | None) -> dict[str, Any]:
        """Return a validation refusal and audit it only for real execution."""
        if not dry_run:
            log = audit if audit is not None else AuditLog(config.log_path)
            log.record(
                ACTION, "skipped", src=source, dst=destination, tier=tier, detail=reason
            )
        return _result(
            False,
            f"Rename skipped: {reason}",
            dry_run=dry_run,
            source=source,
            destination=destination,
            status="skipped",
            detail=reason,
        )

    # --- Refusal 1: path validation (invalid / out-of-root / missing) ---
    allowed, reason = validate_path(path_input, config, must_exist=True)
    if not allowed:
        return skipped(reason, path_input, None)
    source = path_input.resolve()

    # --- Refusal 5: source inside quarantine dir ---
    try:
        if source == quarantine or _is_within(source, quarantine):
            return skipped(
                f"File is inside quarantine and cannot be renamed: {source}",
                source,
                None,
            )
    except OSError as exc:
        return skipped(_detail(exc), source, None)

    # --- Refusal 6: symlink pointing outside root ---
    # validate_path resolves symlinks, so a symlink that escapes the root
    # already fails validate_path above. A symlink inside the root that points
    # inside the root is allowed (it resolves to the target, which is safe).
    # The explicit test lives in tests/test_rename_file.py (F-1).

    # --- Refusal 4: must be a regular file (not directory, not device) ---
    try:
        is_symlink = source.is_symlink()
        is_regular_file = source.is_file()
    except OSError as exc:
        return skipped(_detail(exc), source, None)
    if not is_regular_file:
        try:
            if source.is_dir():
                return skipped(
                    f"Path is a directory, not a regular file: {source}", source, None
                )
        except OSError as exc:
            return skipped(_detail(exc), source, None)
        return skipped(f"Path is not a regular file: {source}", source, None)
    if is_symlink:
        # A symlink to a regular file inside root: rename the link itself, not
        # the target. This matches "rename in place" semantics and avoids
        # surprising the user by moving the target file.
        pass

    # --- Refusals 7-10: new_name validation ---
    name_reason = _validate_new_name(new_name)
    if name_reason is not None:
        return skipped(name_reason, source, source.parent / new_name if isinstance(new_name, str) else None)

    stripped_name = new_name.strip()
    # Normalize: reject leading/trailing whitespace explicitly rather than
    # silently stripping, so the caller's intent is preserved.
    if stripped_name != new_name:
        return skipped(
            "new_name must not have leading or trailing whitespace.",
            source,
            source.parent / new_name,
        )

    # --- Refusal 11: no-op (case-sensitive) ---
    # TASK-0023 + ADR-001 refusal list: src == dst is a refusal, not a silent
    # success. status stays "skipped" (no filesystem mutation) but success must
    # be False so the caller can distinguish "refused" from "done".
    if source.name == new_name:
        detail = f"Source already has that name: {source.name}"
        if not dry_run:
            log = audit if audit is not None else AuditLog(config.log_path)
            log.record(ACTION, "skipped", src=source, dst=source, tier=tier, detail=detail)
        return _result(
            False,
            f"Rename refused: {detail}",
            dry_run=dry_run,
            source=source,
            destination=source,
            status="skipped",
            detail=detail,
        )

    parent = source.parent
    proposed_destination = parent / new_name

    # ADR-001: new_name is NOT a path, so no validate_path(new_name). But the
    # resulting dst must still be inside the allowed root — resolved parent
    # combined with a bare filename can only stay inside the parent, which
    # validate_path already approved. We still validate dst defensively.
    allowed, reason = validate_path(proposed_destination, config, must_exist=False)
    if not allowed:
        return skipped(reason, source, proposed_destination)

    case_only = _is_case_only_rename(source, new_name)
    destination = resolve_collision(proposed_destination) if not case_only else proposed_destination

    # --- Dry run: no user FS mutation, audit reflects planned -> ok ---
    if dry_run:
        log = audit if audit is not None else AuditLog(config.log_path)
        log.planned(ACTION, source, destination, tier=tier)
        log.record(ACTION, "ok", src=source, dst=destination, tier=tier, detail="dry_run")
        return _result(
            True,
            f"Dry run: would rename '{source.name}' to '{destination.name}'.",
            dry_run=True,
            source=source,
            destination=destination,
            status="would_rename",
        )

    log = audit if audit is not None else AuditLog(config.log_path)

    if case_only:
        # Windows-style case-only rename: rename to a unique temp name in the
        # same parent, then rename temp -> final. Two planned/succeeded pairs.
        temp_name = f".__fm_tmp_{uuid.uuid4().hex}__{source.suffix}"
        temp_path = parent / temp_name
        allowed, reason = validate_path(temp_path, config, must_exist=False)
        if not allowed:
            return skipped(reason, source, temp_path)
        temp_destination = resolve_collision(temp_path)

        log.planned(ACTION, source, temp_destination, tier=tier)
        try:
            _move_without_overwrite(source, temp_destination)
        except FileExistsError as exc:
            detail = _detail(exc)
            log.failed(ACTION, source, temp_destination, detail, tier=tier)
            return _result(
                False,
                f"Rename failed: {detail}",
                dry_run=False,
                source=source,
                destination=temp_destination,
                status="failed",
                detail=detail,
            )
        except OSError as exc:
            detail = _detail(exc)
            log.failed(ACTION, source, temp_destination, detail, tier=tier)
            return _result(
                False,
                f"Rename failed: {detail}",
                dry_run=False,
                source=source,
                destination=temp_destination,
                status="failed",
                detail=detail,
            )
        log.succeeded(ACTION, source, temp_destination, tier=tier)

        final_destination = parent / new_name
        allowed, reason = validate_path(final_destination, config, must_exist=False)
        if not allowed:
            return skipped(reason, temp_destination, final_destination)
        # On a case-insensitive FS, final_destination may appear to exist
        # (it is the temp file's own case-folded match). Force the rename
        # without collision resolution.
        log.planned(ACTION, temp_destination, final_destination, tier=tier)
        try:
            os.link(temp_destination, final_destination)
            try:
                os.unlink(temp_destination)
            except OSError:
                try:
                    os.unlink(final_destination)
                except OSError:
                    pass
                raise
        except OSError as exc:
            detail = _detail(exc)
            log.failed(ACTION, temp_destination, final_destination, detail, tier=tier)
            # Best-effort restore of original name.
            try:
                if not source.exists() and temp_destination.exists():
                    os.link(temp_destination, source)
                    os.unlink(temp_destination)
            except OSError:
                pass
            return _result(
                False,
                f"Rename failed: {detail}",
                dry_run=False,
                source=source,
                destination=final_destination,
                status="failed",
                detail=detail,
            )
        log.succeeded(ACTION, temp_destination, final_destination, tier=tier)
        return _result(
            True,
            f"Renamed '{source.name}' to '{final_destination.name}'.",
            dry_run=False,
            source=source,
            destination=final_destination,
            status="renamed",
        )

    # --- Standard (non case-only) rename with collision retry ---
    for attempt in range(_MAX_COLLISION_RETRIES):
        log.planned(ACTION, source, destination, tier=tier)
        try:
            _move_without_overwrite(source, destination)
        except FileExistsError as exc:
            detail = _detail(exc)
            log.failed(ACTION, source, destination, detail, tier=tier)
            destination = resolve_collision(proposed_destination)
            continue
        except OSError as exc:
            detail = _detail(exc)
            log.failed(ACTION, source, destination, detail, tier=tier)
            return _result(
                False,
                f"Rename failed: {detail}",
                dry_run=False,
                source=source,
                destination=destination,
                status="failed",
                detail=detail,
            )

        log.succeeded(ACTION, source, destination, tier=tier)
        return _result(
            True,
            f"Renamed '{source.name}' to '{destination.name}'.",
            dry_run=False,
            source=source,
            destination=destination,
            status="renamed",
        )

    detail = (
        f"Could not claim a free destination after {_MAX_COLLISION_RETRIES} "
        "collision retries."
    )
    return _result(
        False,
        f"Rename failed: {detail}",
        dry_run=False,
        source=source,
        destination=destination,
        status="failed",
        detail=detail,
    )