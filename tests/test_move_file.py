"""Focused safety and execution tests for the one-file Phase 2 move tool."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agent.core.audit import AuditLog
from agent.core.config import Config
from agent.tools.move_file import move_file


def _audit_entries(config: Config) -> list[dict[str, object]]:
    """Read JSONL audit records written by a test execution."""
    return [json.loads(line) for line in config.log_path.read_text(encoding="utf-8").splitlines()]


def test_default_dry_run_changes_nothing(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")
    destination = sandbox / "Documents"
    destination.mkdir()

    result = move_file(source, destination, config)

    assert result["success"]
    assert result["data"]["status"] == "would_move"
    assert source.exists()
    assert not (destination / "report.pdf").exists()


def test_execution_moves_one_file(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")
    destination = sandbox / "Documents"
    destination.mkdir()

    result = move_file(source, destination, config, dry_run=False)

    assert result["success"]
    assert result["data"]["status"] == "moved"
    assert not source.exists()
    assert (destination / "report.pdf").read_text(encoding="utf-8") == "content"


def test_existing_target_uses_first_collision_suffix(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("incoming", encoding="utf-8")
    destination = sandbox / "Documents"
    destination.mkdir()
    (destination / "report.pdf").write_text("original", encoding="utf-8")

    result = move_file(source, destination, config, dry_run=False)

    assert result["data"]["destination"].endswith("report (1).pdf")
    assert (destination / "report.pdf").read_text(encoding="utf-8") == "original"
    assert (destination / "report (1).pdf").read_text(encoding="utf-8") == "incoming"


def test_existing_target_and_first_suffix_uses_second_suffix(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("incoming", encoding="utf-8")
    destination = sandbox / "Documents"
    destination.mkdir()
    (destination / "report.pdf").write_text("original", encoding="utf-8")
    (destination / "report (1).pdf").write_text("first", encoding="utf-8")

    result = move_file(source, destination, config, dry_run=False)

    assert result["data"]["destination"].endswith("report (2).pdf")
    assert (destination / "report (2).pdf").read_text(encoding="utf-8") == "incoming"


def test_dry_run_predicts_collision(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("incoming", encoding="utf-8")
    destination = sandbox / "Documents"
    destination.mkdir()
    (destination / "report.pdf").write_text("original", encoding="utf-8")

    result = move_file(source, destination, config)

    assert result["data"]["destination"].endswith("report (1).pdf")
    assert source.exists()


def test_source_outside_whitelist_is_refused(config: Config, tmp_path: Path, sandbox: Path) -> None:
    source = tmp_path / "outside.pdf"
    source.write_text("content", encoding="utf-8")

    result = move_file(source, sandbox, config, dry_run=False)

    assert not result["success"]
    assert result["data"]["status"] == "skipped"
    assert source.exists()
    assert _audit_entries(config)[0]["status"] == "skipped"


def test_destination_outside_whitelist_is_refused(config: Config, sandbox: Path, tmp_path: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")
    destination = tmp_path / "outside"
    destination.mkdir()

    result = move_file(source, destination, config, dry_run=False)

    assert not result["success"]
    assert result["data"]["status"] == "skipped"
    assert source.exists()


def test_missing_source_is_refused(config: Config, sandbox: Path) -> None:
    destination = sandbox / "Documents"
    destination.mkdir()

    result = move_file(sandbox / "missing.pdf", destination, config)

    assert not result["success"]
    assert result["data"]["status"] == "skipped"
    assert "does not exist" in str(result["data"]["detail"])


def test_missing_destination_is_refused(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")

    result = move_file(source, sandbox / "missing", config)

    assert not result["success"]
    assert result["data"]["status"] == "skipped"
    assert "does not exist" in str(result["data"]["detail"])


def test_destination_file_is_refused(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")
    destination = sandbox / "not-a-folder"
    destination.write_text("content", encoding="utf-8")

    result = move_file(source, destination, config)

    assert not result["success"]
    assert "not a directory" in str(result["data"]["detail"])


def test_parent_traversal_is_refused(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")

    result = move_file(source, sandbox / "..", config)

    assert not result["success"]
    assert "Outside WATCHED_FOLDERS" in str(result["data"]["detail"])


def test_source_directory_is_refused(config: Config, sandbox: Path) -> None:
    source = sandbox / "source-folder"
    source.mkdir()
    destination = sandbox / "Documents"
    destination.mkdir()

    result = move_file(source, destination, config)

    assert not result["success"]
    assert "not a regular file" in str(result["data"]["detail"])


def test_same_parent_is_successful_no_op(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")

    result = move_file(source, sandbox, config, dry_run=False)

    assert result["success"]
    assert result["data"]["status"] == "skipped"
    assert source.exists()
    assert not config.log_path.exists()


def test_vanished_or_locked_source_returns_structured_failure(
    config: Config, sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")
    destination = sandbox / "Documents"
    destination.mkdir()

    def locked_source(_source: Path, _destination: Path) -> None:
        raise PermissionError("source is locked")

    monkeypatch.setattr("agent.tools.move_file._move_without_overwrite", locked_source)
    result = move_file(source, destination, config, dry_run=False)

    assert not result["success"]
    assert result["data"]["status"] == "failed"
    assert source.exists()


def test_success_audit_records_planned_then_ok(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")
    destination = sandbox / "Documents"
    destination.mkdir()

    move_file(source, destination, config, dry_run=False, audit=AuditLog(config.log_path))

    assert [entry["status"] for entry in _audit_entries(config)] == ["planned", "ok"]


def test_failed_audit_records_planned_then_failed(
    config: Config, sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")
    destination = sandbox / "Documents"
    destination.mkdir()

    def locked_source(_source: Path, _destination: Path) -> None:
        raise PermissionError("source is locked")

    monkeypatch.setattr("agent.tools.move_file._move_without_overwrite", locked_source)
    move_file(source, destination, config, dry_run=False)

    assert [entry["status"] for entry in _audit_entries(config)] == ["planned", "failed"]


def test_dry_run_does_not_create_audit_directory(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")
    destination = sandbox / "Documents"
    destination.mkdir()

    move_file(source, destination, config)

    assert not config.log_path.parent.exists()


def test_collision_race_retries_next_suffix_without_overwriting(
    config: Config, sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = sandbox / "report.pdf"
    source.write_text("incoming", encoding="utf-8")
    destination_dir = sandbox / "Documents"
    destination_dir.mkdir()
    (destination_dir / "report.pdf").write_text("original", encoding="utf-8")
    original_move = os.link
    raced = False

    def race(source_path: Path, destination_path: Path) -> None:
        nonlocal raced
        if not raced:
            raced = True
            destination_path.write_text("racer", encoding="utf-8")
            raise FileExistsError("destination became occupied")
        original_move(source_path, destination_path)

    monkeypatch.setattr("agent.tools.move_file.os.link", race)
    result = move_file(source, destination_dir, config, dry_run=False)

    assert result["success"]
    assert result["data"]["destination"].endswith("report (2).pdf")
    assert (destination_dir / "report (1).pdf").read_text(encoding="utf-8") == "racer"
    assert (destination_dir / "report (2).pdf").read_text(encoding="utf-8") == "incoming"
    assert [entry["status"] for entry in _audit_entries(config)] == [
        "planned",
        "failed",
        "planned",
        "ok",
    ]
