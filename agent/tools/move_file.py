"""Safely move one file into an existing, approved destination directory.

This Phase 2 tool deliberately accepts one regular file only.  It does not
create folders, expand globs, or turn a request into a batch.  A dry run is
the default, and a real execution uses an atomic no-overwrite claim for the
destination name before removing the source.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agent.core.audit import AuditLog, Tier
from agent.core.config import Config
from agent.core.safety import validate_path
from agent.tools.organize_files import resolve_collision

ACTION = "move"
_MAX_COLLISION_RETRIES = 100


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


def _move_without_overwrite(source: Path, destination: Path) -> None:
    """Move one same-volume file without ever replacing an existing target.

    ``os.rename`` may replace an already-existing target on POSIX, so it cannot
    uphold FileMind's no-overwrite rule during a check-then-move race.  Creating
    a hard link atomically claims a previously absent target on supported local
    filesystems; removing the original name then completes the move.  A
    cross-volume request fails at ``os.link`` and is intentionally not given a
    copy/delete fallback.
    """
    os.link(source, destination)
    try:
        os.unlink(source)
    except OSError:
        # The destination was just created by this call, so removing it restores
        # the pre-operation namespace if the source name cannot be removed.
        try:
            os.unlink(destination)
        except OSError:
            # Preserve the original failure; the caller records it as a failed
            # attempt.  The remaining extra hard link is safer than deletion.
            pass
        raise


def move_file(
    src: Path | str,
    dst: Path | str,
    config: Config,
    *,
    dry_run: bool = True,
    audit: AuditLog | None = None,
    tier: Tier = "local",
) -> dict[str, Any]:
    """Move one approved regular file into an existing approved directory.

    ``dst`` is a directory rather than a target filename.  The resulting name
    is the source filename, using the project's ``file (n).ext`` collision
    convention when necessary.  With the default ``dry_run=True``, this returns
    the planned target without changing the filesystem or constructing an audit
    log.  Real execution writes audit records for refusals and for each actual
    filesystem attempt.
    """
    try:
        source_input = Path(src).expanduser()
        destination_input = Path(dst).expanduser()
    except (OSError, TypeError, ValueError) as exc:
        detail = f"Invalid path argument: {type(exc).__name__}: {exc}"
        if not dry_run:
            log = audit if audit is not None else AuditLog(config.log_path)
            log.record(ACTION, "skipped", src=str(src), dst=str(dst), tier=tier, detail=detail)
        return _result(
            False,
            f"Move skipped: {detail}",
            dry_run=dry_run,
            source=None,
            destination=None,
            status="skipped",
            detail=detail,
        )

    def skipped(reason: str, source: Path | None, destination: Path | None) -> dict[str, Any]:
        """Return a validation refusal and audit it only for real execution."""
        if not dry_run:
            log = audit if audit is not None else AuditLog(config.log_path)
            log.record(ACTION, "skipped", src=source, dst=destination, tier=tier, detail=reason)
        return _result(
            False,
            f"Move skipped: {reason}",
            dry_run=dry_run,
            source=source,
            destination=destination,
            status="skipped",
            detail=reason,
        )

    allowed, reason = validate_path(source_input, config, must_exist=True)
    if not allowed:
        return skipped(reason, source_input, destination_input)
    source = source_input.resolve()

    try:
        is_regular_file = source.is_file()
    except OSError as exc:
        return skipped(_detail(exc), source, destination_input)
    if not is_regular_file:
        return skipped(f"Source is not a regular file: {source}", source, destination_input)

    allowed, reason = validate_path(destination_input, config, must_exist=True)
    if not allowed:
        return skipped(reason, source, destination_input)
    destination_dir = destination_input.resolve()

    try:
        is_directory = destination_dir.is_dir()
    except OSError as exc:
        return skipped(_detail(exc), source, destination_dir)
    if not is_directory:
        return skipped(
            f"Destination is not a directory: {destination_dir}", source, destination_dir
        )

    proposed_destination = destination_dir / source.name
    allowed, reason = validate_path(proposed_destination, config, must_exist=False)
    if not allowed:
        return skipped(reason, source, proposed_destination)

    if source.parent == destination_dir:
        detail = "Source already resides in the destination directory."
        return _result(
            True,
            "No move needed: source is already in the destination directory.",
            dry_run=dry_run,
            source=source,
            destination=source,
            status="skipped",
            detail=detail,
        )

    destination = resolve_collision(proposed_destination)
    if dry_run:
        return _result(
            True,
            f"Dry run: would move '{source.name}' to '{destination}'.",
            dry_run=True,
            source=source,
            destination=destination,
            status="would_move",
        )

    log = audit if audit is not None else AuditLog(config.log_path)
    for attempt in range(_MAX_COLLISION_RETRIES):
        log.planned(ACTION, source, destination, tier=tier)
        try:
            _move_without_overwrite(source, destination)
        except FileExistsError as exc:
            # Another process claimed the name after collision resolution.  Log
            # that attempt, then select the next available Explorer-style name.
            detail = _detail(exc)
            log.failed(ACTION, source, destination, detail, tier=tier)
            destination = resolve_collision(proposed_destination)
            continue
        except OSError as exc:
            detail = _detail(exc)
            log.failed(ACTION, source, destination, detail, tier=tier)
            return _result(
                False,
                f"Move failed: {detail}",
                dry_run=False,
                source=source,
                destination=destination,
                status="failed",
                detail=detail,
            )

        log.succeeded(ACTION, source, destination, tier=tier)
        return _result(
            True,
            f"Moved '{source.name}' to '{destination}'.",
            dry_run=False,
            source=source,
            destination=destination,
            status="moved",
        )

    detail = f"Could not claim a free destination after {_MAX_COLLISION_RETRIES} collision retries."
    return _result(
        False,
        f"Move failed: {detail}",
        dry_run=False,
        source=source,
        destination=destination,
        status="failed",
        detail=detail,
    )
