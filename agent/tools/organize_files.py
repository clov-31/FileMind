"""Move files into category subfolders.

The only tool in Phase 1 that writes to disk. Three properties matter more than
anything else here, in order:

1. `dry_run` defaults to True (safety rule 3) — the caller must opt in to
   touching disk, not opt out.
2. Nothing is ever overwritten. A name collision produces `name (1).ext`.
3. One bad file cannot abort the batch. Each move is isolated; a locked or
   vanished file is logged and the remaining files still get organized.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.core.audit import AuditLog
from agent.core.config import Config
from agent.core.safety import validate_path

ACTION = "move"


@dataclass(frozen=True)
class Move:
    """One proposed file move: `source` into `category` under the same root."""

    source: Path
    category: str
    tier: str = "rule"


def resolve_collision(destination: Path, claimed: set[Path] | None = None) -> Path:
    """Return a free path, appending ` (n)` if `destination` is taken.

    Windows Explorer convention: `report.pdf` -> `report (1).pdf`. Guarantees
    the returned path neither exists on disk nor appears in `claimed`, so a move
    never destroys an existing file and two files in the same batch never target
    the same name — during a dry run nothing exists yet, so on-disk checks alone
    would hand the same destination to both.
    """
    claimed = claimed or set()

    def taken(path: Path) -> bool:
        return path.exists() or path in claimed

    if not taken(destination):
        return destination

    stem, suffix, parent = destination.stem, destination.suffix, destination.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not taken(candidate):
            return candidate
        counter += 1


def plan_moves(files: list[dict[str, Any]], categories: dict[str, str], root: Path) -> list[Move]:
    """Pair scanned files with their category to produce a move list.

    `categories` maps filename to category name; files missing from it are left
    out rather than guessed at.
    """
    moves: list[Move] = []
    for entry in files:
        category = categories.get(entry["name"])
        if category:
            moves.append(Move(source=Path(entry["path"]), category=category))
    return moves


def organize_files(
    moves: list[Move],
    config: Config,
    *,
    dry_run: bool = True,
    audit: AuditLog | None = None,
) -> dict[str, Any]:
    """Move each file into its category subfolder, or report what would happen.

    With `dry_run=True` (the default) nothing is created, moved, or logged as
    executed — the returned plan shows the exact destination each file would get,
    collision suffixes included. With `dry_run=False` each move is logged as
    `planned` before it is attempted and as `ok`/`failed` after, per safety rule 2.

    Returns `{success, message, data}`; `data["results"]` has one record per file
    with its outcome. A file that fails does not stop the others.
    """
    audit = audit or AuditLog(config.log_path)
    results: list[dict[str, Any]] = []
    moved = failed = skipped = 0

    claimed: set[Path] = set()

    for move in moves:
        source = move.source
        allowed, reason = validate_path(source, config)
        if not allowed:
            results.append({"source": str(source), "status": "skipped", "detail": reason})
            audit.record(ACTION, "skipped", src=source, tier=move.tier, detail=reason)
            skipped += 1
            continue

        source = source.expanduser().resolve()
        target_dir = source.parent / move.category
        destination = target_dir / source.name

        allowed, reason = validate_path(target_dir, config, must_exist=False)
        if not allowed:
            results.append({"source": str(source), "status": "skipped", "detail": reason})
            audit.record(ACTION, "skipped", src=source, dst=destination, tier=move.tier, detail=reason)
            skipped += 1
            continue

        destination = resolve_collision(destination, claimed)
        claimed.add(destination)

        if dry_run:
            results.append(
                {
                    "source": str(source),
                    "destination": str(destination),
                    "category": move.category,
                    "status": "would_move",
                }
            )
            continue

        audit.planned(ACTION, source, destination, tier=move.tier)
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        except (OSError, shutil.Error) as exc:
            # Most commonly a Windows sharing violation: the file is open in
            # another program. Attempting the move and catching the failure is
            # the only reliable check — a pre-check would race anyway.
            detail = f"{type(exc).__name__}: {exc}"
            audit.failed(ACTION, source, destination, detail, tier=move.tier)
            results.append({"source": str(source), "destination": str(destination), "status": "failed", "detail": detail})
            failed += 1
            continue

        audit.succeeded(ACTION, source, destination, tier=move.tier)
        results.append(
            {
                "source": str(source),
                "destination": str(destination),
                "category": move.category,
                "status": "moved",
            }
        )
        moved += 1

    if dry_run:
        message = f"Dry run: {len(results)} file(s) would be moved, {skipped} skipped. Nothing changed."
    else:
        message = f"Moved {moved} file(s); {failed} failed, {skipped} skipped."

    return {
        "success": failed == 0,
        "message": message,
        "data": {
            "dry_run": dry_run,
            "results": results,
            "counts": {"moved": moved, "failed": failed, "skipped": skipped},
        },
    }
