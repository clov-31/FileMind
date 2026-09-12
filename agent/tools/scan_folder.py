"""Scan a watched folder and report the loose files in it.

Read-only. This tool never modifies anything; it exists so the rest of the
pipeline has an accurate, already-filtered picture of what is sitting in a
folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent.core.classify import CATEGORY_NAMES
from agent.core.config import Config
from agent.core.safety import validate_path

# Partially-downloaded files. Moving one mid-download corrupts it and confuses
# the browser that is still writing to it.
IN_PROGRESS_SUFFIXES: frozenset[str] = frozenset(
    {".crdownload", ".part", ".partial", ".tmp", ".download", ".!ut"}
)

# Folders the agent itself creates. Skipping them is what makes a second run a
# no-op instead of re-filing everything the first run just organized.
_SKIP_DIR_NAMES: frozenset[str] = frozenset(name.lower() for name in CATEGORY_NAMES) | {"_quarantine"}


def _is_hidden(entry: Path) -> bool:
    """True for dotfiles and Windows hidden/system files."""
    if entry.name.startswith("."):
        return True
    try:
        import stat

        attrs = entry.stat().st_file_attributes  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return False
    return bool(attrs & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM))


def scan_folder(folder: str | Path, config: Config) -> dict[str, Any]:
    """List the loose files in a watched folder that are candidates for organizing.

    Looks at the top level only — nested folders are left alone entirely in this
    phase. Returns `{success, message, data}` where `data` holds `files` (the
    movable entries, each with name/path/ext/size_bytes/mtime) and `skipped`
    (counts by reason, so the CLI can explain what it ignored and why).

    Skips directories, the agent's own destination folders, in-progress
    downloads, and hidden/system files.
    """
    allowed, reason = validate_path(folder, config)
    if not allowed:
        return {"success": False, "message": f"Refused to scan {folder}: {reason}", "data": {}}

    root = Path(folder).expanduser().resolve()

    files: list[dict[str, Any]] = []
    skipped = {"directories": 0, "agent_folders": 0, "in_progress": 0, "hidden": 0, "unreadable": 0}

    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
    except OSError as exc:
        return {"success": False, "message": f"Could not read {root}: {exc}", "data": {}}

    for entry in entries:
        try:
            if entry.is_dir():
                if entry.name.lower() in _SKIP_DIR_NAMES:
                    skipped["agent_folders"] += 1
                else:
                    skipped["directories"] += 1
                continue

            if _is_hidden(entry):
                skipped["hidden"] += 1
                continue

            if entry.suffix.lower() in IN_PROGRESS_SUFFIXES:
                skipped["in_progress"] += 1
                continue

            stat_result = entry.stat()
        except OSError:
            skipped["unreadable"] += 1
            continue

        files.append(
            {
                "name": entry.name,
                "path": str(entry),
                "ext": entry.suffix.lower(),
                "size_bytes": stat_result.st_size,
                "mtime": stat_result.st_mtime,
            }
        )

    total_skipped = sum(skipped.values())
    return {
        "success": True,
        "message": f"Found {len(files)} loose file(s) in {root} ({total_skipped} entr(ies) skipped).",
        "data": {"folder": str(root), "files": files, "skipped": skipped},
    }
