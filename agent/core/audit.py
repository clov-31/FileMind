"""Append-only audit trail for every file operation.

Safety rule 2 requires logging *before* executing, so an action is two entries:
`planned` written before the move is attempted, then `ok` or `failed` after. A
crash mid-move therefore leaves a `planned` line with no outcome — which is the
point. A log written only on success cannot tell you what was in flight when
something went wrong.

One JSON object per line so the file stays greppable and machine-readable.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Literal

Status = Literal["planned", "ok", "failed", "skipped"]
Tier = Literal["rule", "local", "cloud", "user"]

_write_lock = threading.Lock()


class AuditLog:
    """Writes timestamped action records to a JSONL file."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        action: str,
        status: Status,
        *,
        src: Path | str | None = None,
        dst: Path | str | None = None,
        tier: Tier = "rule",
        detail: str = "",
    ) -> None:
        """Append one action record.

        Never raises: a failure to log must not take down a run that is midway
        through moving files. A logging problem is reported to stderr and the
        run continues.
        """
        entry = {
            "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
            "action": action,
            "status": status,
            "src": str(src) if src is not None else None,
            "dst": str(dst) if dst is not None else None,
            "tier": tier,
            "detail": detail,
        }
        line = json.dumps(entry, ensure_ascii=False)
        try:
            with _write_lock:
                with self.log_path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
        except OSError as exc:  # pragma: no cover - disk-level failure
            import sys

            print(f"[audit] could not write to {self.log_path}: {exc}", file=sys.stderr)

    def planned(self, action: str, src: Path | str, dst: Path | str, tier: Tier = "rule") -> None:
        """Record an intended action before attempting it."""
        self.record(action, "planned", src=src, dst=dst, tier=tier)

    def succeeded(self, action: str, src: Path | str, dst: Path | str, tier: Tier = "rule") -> None:
        """Record that a previously planned action completed."""
        self.record(action, "ok", src=src, dst=dst, tier=tier)

    def failed(self, action: str, src: Path | str, dst: Path | str, detail: str, tier: Tier = "rule") -> None:
        """Record that a previously planned action did not complete, and why."""
        self.record(action, "failed", src=src, dst=dst, tier=tier, detail=detail)
