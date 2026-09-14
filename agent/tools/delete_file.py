"""Safely quarantine one file by moving it into the configured quarantine folder.

Permanent deletion is never performed. A dry run is the default, and real
execution uses the same atomic no-overwrite move strategy as ``move_file``.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.core.audit import AuditLog, Tier
from agent.core.config import REPO_ROOT, Config
from agent.core.safety import validate_path

ACTION = "delete"
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


def _quarantine_destination(quarantine: Path, source: Path) -> Path:
    """Pick a quarantine filename using the original name plus a timestamp suffix."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = source.stem
    suffix = source.suffix
    candidate = quarantine / f"{stem}_{timestamp}{suffix}"
    counter = 0
    while candidate.exists():
        counter += 1
        candidate = quarantine / f"{stem}_{timestamp}_{counter}{suffix}"
    return candidate


def _move_without_overwrite(source: Path, destination: Path) -> None:
    """Move one same-volume file without ever replacing an existing target."""
    os.link(source, destination)
    try:
        os.unlink(source)
    except OSError:
        try:
            os.unlink(destination)
        except OSError:
            pass
        raise


def delete_file(
    path: Path | str,
    config: Config,
    *,
    dry_run: bool = True,
    audit: AuditLog | None = None,
    tier: Tier = "local",
) -> dict[str, Any]:
    """Move one approved regular file into quarantine (never permanent delete).

    With the default ``dry_run=True``, this records planned and completed audit
    entries but does not change the filesystem. Real execution creates the
    quarantine folder when missing, then moves the file using a timestamped name
    to avoid collisions.
    """
    try:
        path_input = Path(path).expanduser()
    except (OSError, TypeError, ValueError) as exc:
        detail = f"Invalid path argument: {type(exc).__name__}: {exc}"
        if not dry_run:
            log = audit if audit is not None else AuditLog(config.log_path)
            log.record(ACTION, "skipped", src=str(path), dst=None, tier=tier, detail=detail)
        return _result(
            False,
            f"Delete skipped: {detail}",
            dry_run=dry_run,
            source=None,
            destination=None,
            status="skipped",
            detail=detail,
        )

    quarantine = _quarantine_dir(config)

    try:
        resolved_for_quarantine = path_input.resolve()
    except (OSError, ValueError):
        resolved_for_quarantine = None

    if resolved_for_quarantine is not None and resolved_for_quarantine.exists():
        try:
            if resolved_for_quarantine == quarantine or (
                resolved_for_quarantine.is_dir() and resolved_for_quarantine == quarantine
            ):
                return _result(
                    False,
                    f"Delete skipped: Cannot quarantine the quarantine directory itself: {quarantine}",
                    dry_run=dry_run,
                    source=resolved_for_quarantine,
                    destination=quarantine,
                    status="skipped",
                    detail=f"Cannot quarantine the quarantine directory itself: {quarantine}",
                )
            if _is_within(resolved_for_quarantine, quarantine):
                detail = f"File is already inside quarantine: {resolved_for_quarantine}"
                if not dry_run:
                    log = audit if audit is not None else AuditLog(config.log_path)
                    log.record(ACTION, "skipped", src=resolved_for_quarantine, dst=quarantine, tier=tier, detail=detail)
                return _result(
                    False,
                    f"Delete skipped: {detail}",
                    dry_run=dry_run,
                    source=resolved_for_quarantine,
                    destination=quarantine,
                    status="skipped",
                    detail=detail,
                )
        except OSError as exc:
            return _result(
                False,
                f"Delete skipped: {_detail(exc)}",
                dry_run=dry_run,
                source=resolved_for_quarantine,
                destination=quarantine,
                status="skipped",
                detail=_detail(exc),
            )

    def skipped(reason: str, source: Path | None, destination: Path | None) -> dict[str, Any]:
        """Return a validation refusal and audit it only for real execution."""
        if not dry_run:
            log = audit if audit is not None else AuditLog(config.log_path)
            log.record(ACTION, "skipped", src=source, dst=destination, tier=tier, detail=reason)
        return _result(
            False,
            f"Delete skipped: {reason}",
            dry_run=dry_run,
            source=source,
            destination=destination,
            status="skipped",
            detail=reason,
        )

    allowed, reason = validate_path(path_input, config, must_exist=True)
    if not allowed:
        return skipped(reason, path_input, quarantine)
    source = path_input.resolve()

    try:
        is_regular_file = source.is_file()
    except OSError as exc:
        return skipped(_detail(exc), source, quarantine)
    if not is_regular_file:
        try:
            if source.is_dir():
                return skipped(f"Path is a directory, not a regular file: {source}", source, quarantine)
        except OSError as exc:
            return skipped(_detail(exc), source, quarantine)
        return skipped(f"Path is not a regular file: {source}", source, quarantine)

    destination = _quarantine_destination(quarantine, source)

    if dry_run:
        log = audit if audit is not None else AuditLog(config.log_path)
        log.planned(ACTION, source, destination, tier=tier)
        log.record(ACTION, "ok", src=source, dst=destination, tier=tier, detail="dry_run")
        return _result(
            True,
            f"Dry run: would quarantine '{source.name}' as '{destination.name}'.",
            dry_run=True,
            source=source,
            destination=destination,
            status="would_quarantine",
        )

    quarantine.mkdir(parents=True, exist_ok=True)
    log = audit if audit is not None else AuditLog(config.log_path)
    for attempt in range(_MAX_COLLISION_RETRIES):
        log.planned(ACTION, source, destination, tier=tier)
        try:
            _move_without_overwrite(source, destination)
        except FileExistsError as exc:
            detail = _detail(exc)
            log.failed(ACTION, source, destination, detail, tier=tier)
            destination = _quarantine_destination(quarantine, source)
            continue
        except OSError as exc:
            detail = _detail(exc)
            log.failed(ACTION, source, destination, detail, tier=tier)
            return _result(
                False,
                f"Delete failed: {detail}",
                dry_run=False,
                source=source,
                destination=destination,
                status="failed",
                detail=detail,
            )

        log.succeeded(ACTION, source, destination, tier=tier)
        return _result(
            True,
            f"Quarantined '{source.name}' as '{destination.name}'.",
            dry_run=False,
            source=source,
            destination=destination,
            status="quarantined",
        )

    detail = f"Could not claim a free quarantine name after {_MAX_COLLISION_RETRIES} collision retries."
    return _result(
        False,
        f"Delete failed: {detail}",
        dry_run=False,
        source=source,
        destination=destination,
        status="failed",
        detail=detail,
    )
