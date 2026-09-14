"""Focused safety and execution tests for the one-file Phase 2 quarantine tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.core.audit import AuditLog
from agent.core.config import Config
from agent.tools.delete_file import delete_file


def _audit_entries(config: Config) -> list[dict[str, object]]:
    """Read JSONL audit records written by a test execution."""
    return [json.loads(line) for line in config.log_path.read_text(encoding="utf-8").splitlines()]


def _quarantine(config: Config) -> Path:
    assert config.quarantine_folder is not None
    return config.quarantine_folder


def test_default_dry_run_changes_nothing(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")

    result = delete_file(source, config)

    assert result["success"]
    assert result["data"]["status"] == "would_quarantine"
    assert source.exists()
    assert not _quarantine(config).exists()


def test_execution_moves_file_to_quarantine(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")

    result = delete_file(source, config, dry_run=False)

    assert result["success"]
    assert result["data"]["status"] == "quarantined"
    assert not source.exists()
    quarantine = _quarantine(config)
    assert quarantine.is_dir()
    quarantined = quarantine / Path(str(result["data"]["destination"])).name
    assert quarantined.read_text(encoding="utf-8") == "content"
    assert quarantined.name.startswith("report_")
    assert quarantined.suffix == ".pdf"


def test_dry_run_writes_planned_and_ok_audit(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")

    delete_file(source, config, audit=AuditLog(config.log_path))

    entries = _audit_entries(config)
    assert [entry["status"] for entry in entries] == ["planned", "ok"]
    assert entries[-1]["detail"] == "dry_run"
    assert source.exists()


def test_nonexistent_path_is_refused(config: Config, sandbox: Path) -> None:
    result = delete_file(sandbox / "missing.pdf", config, dry_run=False)

    assert not result["success"]
    assert result["data"]["status"] == "skipped"
    assert "does not exist" in str(result["data"]["detail"])


def test_out_of_root_path_is_refused(config: Config, tmp_path: Path, sandbox: Path) -> None:
    source = tmp_path / "outside.pdf"
    source.write_text("content", encoding="utf-8")

    result = delete_file(source, config, dry_run=False)

    assert not result["success"]
    assert result["data"]["status"] == "skipped"
    assert source.exists()
    assert _audit_entries(config)[0]["status"] == "skipped"


def test_directory_input_is_refused(config: Config, sandbox: Path) -> None:
    source = sandbox / "folder"
    source.mkdir()

    result = delete_file(source, config)

    assert not result["success"]
    assert "directory" in str(result["data"]["detail"]).lower()


def test_quarantine_dir_input_is_refused(config: Config, sandbox: Path) -> None:
    quarantine = _quarantine(config)
    quarantine.mkdir(parents=True)

    result = delete_file(quarantine, config)

    assert not result["success"]
    assert "quarantine directory" in str(result["data"]["detail"]).lower()


def test_file_already_in_quarantine_is_refused(config: Config, sandbox: Path) -> None:
    quarantine = _quarantine(config)
    quarantine.mkdir(parents=True)
    inside = quarantine / "leftover.pdf"
    inside.write_text("content", encoding="utf-8")

    result = delete_file(inside, config, dry_run=False)

    assert not result["success"]
    assert "already inside quarantine" in str(result["data"]["detail"]).lower()
    assert inside.exists()


def test_collision_uses_timestamp_suffix(config: Config, sandbox: Path) -> None:
    quarantine = _quarantine(config)
    quarantine.mkdir(parents=True)
    (quarantine / "report_20260101-120000.pdf").write_text("first", encoding="utf-8")

    source = sandbox / "report.pdf"
    source.write_text("second", encoding="utf-8")

    result = delete_file(source, config, dry_run=False)

    assert result["success"]
    dest_name = Path(str(result["data"]["destination"])).name
    assert dest_name != "report_20260101-120000.pdf"
    assert dest_name.startswith("report_")
    assert (quarantine / dest_name).read_text(encoding="utf-8") == "second"


def test_sequential_same_name_deletes_get_distinct_names(
    config: Config, sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quarantine = _quarantine(config)
    quarantine.mkdir(parents=True)
    timestamps = iter(["20260101-120000", "20260101-120000"])

    class FixedDateTime:
        @staticmethod
        def now() -> object:
            class _Now:
                def strftime(self, _fmt: str) -> str:
                    return next(timestamps)

            return _Now()

    monkeypatch.setattr("agent.tools.delete_file.datetime", FixedDateTime)

    first = sandbox / "report.pdf"
    first.write_text("first", encoding="utf-8")

    first_result = delete_file(first, config, dry_run=False)

    second = sandbox / "report.pdf"
    second.write_text("second", encoding="utf-8")
    second_result = delete_file(second, config, dry_run=False)

    assert first_result["success"]
    assert second_result["success"]
    first_name = Path(str(first_result["data"]["destination"])).name
    second_name = Path(str(second_result["data"]["destination"])).name
    assert first_name != second_name
    assert second_name.endswith("_1.pdf")


def test_empty_path_is_refused(config: Config, sandbox: Path) -> None:
    result = delete_file("", config)

    assert not result["success"]
    assert result["data"]["status"] == "skipped"


def test_trailing_slash_path_is_accepted_for_file(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")
    path_with_slash = str(source) + "\\"

    result = delete_file(path_with_slash, config, dry_run=False)

    assert result["success"]
    assert not source.exists()


def test_success_audit_records_planned_then_ok(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")

    delete_file(source, config, dry_run=False, audit=AuditLog(config.log_path))

    assert [entry["status"] for entry in _audit_entries(config)] == ["planned", "ok"]


def test_failed_audit_records_planned_then_failed(
    config: Config, sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = sandbox / "report.pdf"
    source.write_text("content", encoding="utf-8")

    def locked_move(_source: Path, _destination: Path) -> None:
        raise PermissionError("source is locked")

    monkeypatch.setattr("agent.tools.delete_file._move_without_overwrite", locked_move)
    delete_file(source, config, dry_run=False)

    assert [entry["status"] for entry in _audit_entries(config)] == ["planned", "failed"]
    assert source.exists()
