"""organize_files: dry-run default, no overwrites, per-file error isolation."""

from __future__ import annotations

import json
from pathlib import Path

from agent.core.audit import AuditLog
from agent.core.config import Config
from agent.tools.organize_files import Move, organize_files, resolve_collision
from tests.conftest import make_files


def test_dry_run_is_the_default_and_changes_nothing(config: Config, sandbox: Path) -> None:
    """Safety rule 3: the caller must opt in to touching disk."""
    make_files(sandbox, ["a.pdf"])
    moves = [Move(source=sandbox / "a.pdf", category="Documents")]

    result = organize_files(moves, config)  # no dry_run argument

    assert result["data"]["dry_run"] is True
    assert (sandbox / "a.pdf").exists()
    assert not (sandbox / "Documents").exists()
    assert result["data"]["results"][0]["status"] == "would_move"


def test_execute_moves_the_file(config: Config, sandbox: Path) -> None:
    make_files(sandbox, ["a.pdf"])
    moves = [Move(source=sandbox / "a.pdf", category="Documents")]

    result = organize_files(moves, config, dry_run=False)

    assert result["success"]
    assert (sandbox / "Documents" / "a.pdf").exists()
    assert not (sandbox / "a.pdf").exists()


def test_collision_suffixes_instead_of_overwriting(config: Config, sandbox: Path) -> None:
    """The existing file's contents must survive untouched."""
    (sandbox / "Documents").mkdir()
    (sandbox / "Documents" / "a.pdf").write_text("ORIGINAL", encoding="utf-8")
    (sandbox / "a.pdf").write_text("INCOMING", encoding="utf-8")

    organize_files([Move(sandbox / "a.pdf", "Documents")], config, dry_run=False)

    assert (sandbox / "Documents" / "a.pdf").read_text(encoding="utf-8") == "ORIGINAL"
    assert (sandbox / "Documents" / "a (1).pdf").read_text(encoding="utf-8") == "INCOMING"


def test_dry_run_shows_the_collision_suffix_it_would_use(config: Config, sandbox: Path) -> None:
    """The preview must match what execution will actually do, suffixes included."""
    (sandbox / "Documents").mkdir()
    (sandbox / "Documents" / "a.pdf").write_text("existing", encoding="utf-8")
    make_files(sandbox, ["a.pdf"])

    result = organize_files([Move(sandbox / "a.pdf", "Documents")], config, dry_run=True)

    assert result["data"]["results"][0]["destination"].endswith("a (1).pdf")


def test_one_failure_does_not_abort_the_batch(config: Config, sandbox: Path) -> None:
    """A vanished file is reported and the rest still get organized."""
    make_files(sandbox, ["good1.pdf", "good2.pdf"])
    moves = [
        Move(sandbox / "good1.pdf", "Documents"),
        Move(sandbox / "ghost.pdf", "Documents"),  # never existed
        Move(sandbox / "good2.pdf", "Documents"),
    ]

    result = organize_files(moves, config, dry_run=False)

    assert (sandbox / "Documents" / "good1.pdf").exists()
    assert (sandbox / "Documents" / "good2.pdf").exists()
    assert result["data"]["counts"]["moved"] == 2
    assert result["data"]["counts"]["skipped"] == 1


def test_sources_outside_the_whitelist_are_refused(config: Config, tmp_path: Path) -> None:
    outsider = tmp_path / "outside.pdf"
    outsider.write_text("x", encoding="utf-8")

    result = organize_files([Move(outsider, "Documents")], config, dry_run=False)

    assert result["data"]["counts"]["skipped"] == 1
    assert outsider.exists()


def test_audit_logs_planned_before_outcome(config: Config, sandbox: Path) -> None:
    """Safety rule 2: the intent is on disk before the move is attempted."""
    make_files(sandbox, ["a.pdf"])
    audit = AuditLog(config.log_path)

    organize_files([Move(sandbox / "a.pdf", "Documents")], config, dry_run=False, audit=audit)

    lines = [json.loads(l) for l in config.log_path.read_text(encoding="utf-8").splitlines()]
    statuses = [entry["status"] for entry in lines]
    assert statuses == ["planned", "ok"]
    assert lines[0]["src"].endswith("a.pdf")
    assert lines[1]["dst"].endswith("a.pdf")


def test_dry_run_writes_no_audit_entries(config: Config, sandbox: Path) -> None:
    make_files(sandbox, ["a.pdf"])
    organize_files([Move(sandbox / "a.pdf", "Documents")], config, dry_run=True)
    assert not config.log_path.exists() or config.log_path.read_text(encoding="utf-8") == ""


def test_resolve_collision_counts_up(tmp_path: Path) -> None:
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "a (1).pdf").write_text("x", encoding="utf-8")
    assert resolve_collision(tmp_path / "a.pdf").name == "a (2).pdf"


def test_resolve_collision_respects_claimed_paths(tmp_path: Path) -> None:
    claimed = {tmp_path / "a.pdf"}
    assert resolve_collision(tmp_path / "a.pdf", claimed).name == "a (1).pdf"
