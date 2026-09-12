"""Phase 1 CLI: scan a folder, propose moves, execute only on confirmation.

Dry run is the default. Disk is touched only when the user passes `--execute`
*and* answers the confirmation prompt.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from agent.core.audit import AuditLog
from agent.core.classify import classify
from agent.core.config import Config, ConfigError, load_config
from agent.tools.organize_files import Move, organize_files
from agent.tools.scan_folder import scan_folder

SAMPLE_PER_CATEGORY = 3


def _print_proposal(moves: list[Move], skipped: dict[str, int]) -> None:
    """Print the proposed moves grouped by category, with a few samples each."""
    by_category: dict[str, list[Move]] = defaultdict(list)
    for move in moves:
        by_category[move.category].append(move)

    print()
    print(f"  {'Category':<16} {'Files':>5}   Examples")
    print(f"  {'-' * 16} {'-' * 5}   {'-' * 40}")
    for category in sorted(by_category):
        group = by_category[category]
        samples = ", ".join(m.source.name for m in group[:SAMPLE_PER_CATEGORY])
        if len(group) > SAMPLE_PER_CATEGORY:
            samples += f", +{len(group) - SAMPLE_PER_CATEGORY} more"
        print(f"  {category:<16} {len(group):>5}   {samples}")
    print()

    reasons = {
        "directories": "folder(s) left alone",
        "agent_folders": "already-organized folder(s)",
        "in_progress": "in-progress download(s)",
        "hidden": "hidden/system file(s)",
        "unreadable": "unreadable entr(ies)",
    }
    noted = [f"{count} {reasons[key]}" for key, count in skipped.items() if count]
    if noted:
        print("  Skipped: " + "; ".join(noted))
        print()


def _confirm(count: int, threshold: int) -> bool:
    """Ask for explicit consent when a batch exceeds the configured threshold.

    Safety rule 6: bulk actions need a typed yes from the user. Nothing in the
    agent can approve this on the user's behalf.
    """
    if count <= threshold:
        return True

    print(f"  This will move {count} files, above the confirmation threshold of {threshold}.")
    try:
        answer = input("  Type 'yes' to proceed, anything else to cancel: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer == "yes"


def run_scan(config: Config, folder: Path, *, execute: bool, use_llm: bool) -> int:
    """Run the Phase 1 pipeline against one folder. Returns a process exit code."""
    audit = AuditLog(config.log_path)

    scan = scan_folder(folder, config)
    if not scan["success"]:
        print(f"  {scan['message']}", file=sys.stderr)
        return 1

    files = scan["data"]["files"]
    print(f"  {scan['message']}")
    if not files:
        return 0

    classifications = classify([f["name"] for f in files], config, use_llm=use_llm)
    categories = {c.name: c.category for c in classifications}
    tiers = {c.name: c.tier for c in classifications}

    moves = [
        Move(source=Path(f["path"]), category=categories[f["name"]], tier=tiers[f["name"]])
        for f in files
        if f["name"] in categories
    ]

    _print_proposal(moves, scan["data"]["skipped"])

    if not execute:
        preview = organize_files(moves, config, dry_run=True, audit=audit)
        print(f"  {preview['message']}")
        print("  Re-run with --execute to apply.")
        return 0

    if not _confirm(len(moves), config.batch_confirm_threshold):
        print("  Cancelled. Nothing was moved.")
        audit.record("organize", "skipped", src=folder, tier="user", detail="user declined confirmation")
        return 0

    result = organize_files(moves, config, dry_run=False, audit=audit)
    print(f"  {result['message']}")

    for record in result["data"]["results"]:
        if record["status"] in {"failed", "skipped"}:
            print(f"    ! {Path(record['source']).name}: {record.get('detail', '')}")

    print(f"  Audit log: {config.log_path}")
    return 0 if result["success"] else 1


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m agent",
        description="Local-first file organizer. Dry run unless --execute is given.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="scan a watched folder and propose moves")
    scan.add_argument(
        "--folder",
        type=Path,
        default=None,
        help="folder to scan (default: first entry in WATCHED_FOLDERS)",
    )
    scan.add_argument(
        "--execute",
        action="store_true",
        help="actually move files, after confirmation (default: dry run)",
    )
    scan.add_argument(
        "--no-llm",
        action="store_true",
        help="skip the local model entirely; classify by extension rules only",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for `python -m agent`."""
    args = build_parser().parse_args(argv)

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"  Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.command == "scan":
        folder = args.folder or config.watched_folders[0]
        return run_scan(config, folder, execute=args.execute, use_llm=not args.no_llm)

    return 2
