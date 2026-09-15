"""Focused safety and execution tests for the one-file Phase 2 rename tool."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from agent.core.audit import AuditLog
from agent.core.config import Config
from agent.tools.rename_file import rename_file


def _audit_entries(config: Config) -> list[dict[str, object]]:
    """Read JSONL audit records written by a test execution."""
    return [json.loads(line) for line in config.log_path.read_text(encoding="utf-8").splitlines()]


def _can_create_symlinks(tmp_path: Path) -> bool:
    """True if the current user can create symlinks (Windows privilege check)."""
    if sys.platform != "win32":
        return True
    target = tmp_path / "__symlink_probe_target__"
    link = tmp_path / "__symlink_probe_link__"
    try:
        target.write_text("x", encoding="utf-8")
        link.symlink_to(target)
        link.unlink()
        target.unlink()
        return True
    except (OSError, NotImplementedError):
        try:
            if link.exists() or link.is_symlink():
                link.unlink()
        except OSError:
            pass
        try:
            if target.exists():
                target.unlink()
        except OSError:
            pass
        return False


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_default_dry_run_changes_nothing(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "renamed.txt", config)

    assert result["success"]
    assert result["data"]["status"] == "would_rename"
    assert result["data"]["dry_run"] is True
    assert source.exists()
    assert not (sandbox / "renamed.txt").exists()


def test_execution_renames_in_place(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "renamed.txt", config, dry_run=False)

    assert result["success"]
    assert result["data"]["status"] == "renamed"
    assert not source.exists()
    assert (sandbox / "renamed.txt").read_text(encoding="utf-8") == "content"
    # Same parent directory
    assert Path(str(result["data"]["destination"])).parent == sandbox


def test_destination_stays_in_same_parent(config: Config, sandbox: Path) -> None:
    nested = sandbox / "nested"
    nested.mkdir()
    source = nested / "report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "renamed.txt", config, dry_run=False)

    assert result["success"]
    assert (nested / "renamed.txt").exists()
    assert not (sandbox / "renamed.txt").exists()


# ---------------------------------------------------------------------------
# Refusals — path side
# ---------------------------------------------------------------------------

def test_nonexistent_path_is_refused(config: Config, sandbox: Path) -> None:
    result = rename_file(sandbox / "missing.txt", "new.txt", config, dry_run=False)

    assert not result["success"]
    assert result["data"]["status"] == "skipped"
    assert "does not exist" in str(result["data"]["detail"])


def test_out_of_root_path_is_refused(config: Config, tmp_path: Path, sandbox: Path) -> None:
    source = tmp_path / "outside.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "renamed.txt", config, dry_run=False)

    assert not result["success"]
    assert result["data"]["status"] == "skipped"
    assert source.exists()
    assert _audit_entries(config)[0]["status"] == "skipped"


def test_directory_input_is_refused(config: Config, sandbox: Path) -> None:
    source = sandbox / "folder"
    source.mkdir()

    result = rename_file(source, "renamed.txt", config)

    assert not result["success"]
    assert "directory" in str(result["data"]["detail"]).lower()


def test_quarantine_dir_input_is_refused(config: Config, sandbox: Path) -> None:
    assert config.quarantine_folder is not None
    quarantine = config.quarantine_folder
    quarantine.mkdir(parents=True, exist_ok=True)
    inside = quarantine / "leftover.txt"
    inside.write_text("content", encoding="utf-8")

    result = rename_file(inside, "renamed.txt", config, dry_run=False)

    assert not result["success"]
    assert "quarantine" in str(result["data"]["detail"]).lower()
    assert inside.exists()


def test_quarantine_dir_itself_is_refused(config: Config) -> None:
    assert config.quarantine_folder is not None
    quarantine = config.quarantine_folder
    quarantine.mkdir(parents=True, exist_ok=True)

    result = rename_file(quarantine, "renamed.txt", config)

    assert not result["success"]
    assert "quarantine" in str(result["data"]["detail"]).lower()


@pytest.mark.skipif(
    sys.platform == "win32" and not _can_create_symlinks(Path.cwd()),
    reason="Symlink creation requires privilege on this Windows host.",
)
def test_symlink_pointing_outside_root_is_refused(
    config: Config, sandbox: Path, tmp_path: Path
) -> None:
    outside_target = tmp_path / "outside_target.txt"
    outside_target.write_text("outside", encoding="utf-8")

    link = sandbox / "link.txt"
    try:
        link.symlink_to(outside_target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not permitted on this host.")

    # Dry-run is safe to assert even if the platform can't create the link.
    result = rename_file(link, "renamed.txt", config)

    assert not result["success"]
    assert result["data"]["status"] == "skipped"
    assert link.is_symlink()


# ---------------------------------------------------------------------------
# Refusals — new_name side
# ---------------------------------------------------------------------------

def test_new_name_with_slash_is_refused(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "sub/new.txt", config, dry_run=False)

    assert not result["success"]
    assert "/" in str(result["data"]["detail"]) or "bare filename" in str(result["data"]["detail"])
    assert source.exists()


def test_new_name_with_backslash_is_refused(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "sub\\new.txt", config, dry_run=False)

    assert not result["success"]
    assert source.exists()


def test_new_name_with_dotdot_is_refused(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "..", config, dry_run=False)

    assert not result["success"]
    assert source.exists()


def test_new_name_with_embedded_dotdot_is_refused(config: Config, sandbox: Path) -> None:
    """ADR-004 decision: literal '..' anywhere is refused, even harmless."""
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "foo..bar.txt", config, dry_run=False)

    assert not result["success"]
    assert ".." in str(result["data"]["detail"])
    assert source.exists()


def test_empty_new_name_is_refused(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "", config, dry_run=False)

    assert not result["success"]
    assert source.exists()


def test_whitespace_only_new_name_is_refused(config: Config, sandbox: Path) -> None:
    """ADR-004 decision: whitespace-only is refused as empty after strip."""
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "   ", config, dry_run=False)

    assert not result["success"]
    assert source.exists()


def test_same_name_is_refused_as_noop(config: Config, sandbox: Path) -> None:
    """TASK-0023 / ADR-001: src == dst is a REFUSAL, not a silent success."""
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "report.txt", config, dry_run=False)

    assert result["success"] is False
    assert result["data"]["status"] == "skipped"
    assert "already" in str(result["data"]["detail"]).lower()
    assert source.exists()


# ---------------------------------------------------------------------------
# Collision handling — forced, not vacuous (F-2)
# ---------------------------------------------------------------------------

def test_collision_forced_by_precreating_exact_candidate(
    config: Config, sandbox: Path
) -> None:
    """Force a real collision: the candidate name must already exist."""
    source = sandbox / "report.txt"
    source.write_text("incoming", encoding="utf-8")
    (sandbox / "renamed.txt").write_text("original", encoding="utf-8")

    result = rename_file(source, "renamed.txt", config, dry_run=False)

    assert result["success"]
    dest_name = Path(str(result["data"]["destination"])).name
    assert dest_name == "renamed (1).txt"
    assert (sandbox / "renamed.txt").read_text(encoding="utf-8") == "original"
    assert (sandbox / "renamed (1).txt").read_text(encoding="utf-8") == "incoming"


def test_double_collision_uses_second_suffix(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.txt"
    source.write_text("incoming", encoding="utf-8")
    (sandbox / "renamed.txt").write_text("original", encoding="utf-8")
    (sandbox / "renamed (1).txt").write_text("first", encoding="utf-8")

    result = rename_file(source, "renamed.txt", config, dry_run=False)

    assert result["success"]
    dest_name = Path(str(result["data"]["destination"])).name
    assert dest_name == "renamed (2).txt"
    assert (sandbox / "renamed (2).txt").read_text(encoding="utf-8") == "incoming"


def test_dry_run_predicts_collision(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.txt"
    source.write_text("incoming", encoding="utf-8")
    (sandbox / "renamed.txt").write_text("original", encoding="utf-8")

    result = rename_file(source, "renamed.txt", config)

    assert result["data"]["status"] == "would_rename"
    assert Path(str(result["data"]["destination"])).name == "renamed (1).txt"
    assert source.exists()


# ---------------------------------------------------------------------------
# Case-only rename (Windows)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(sys.platform != "win32", reason="Case-only rename is a Windows-specific path.")
def test_case_only_rename_on_windows(config: Config, sandbox: Path) -> None:
    source = sandbox / "Report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "report.txt", config, dry_run=False)

    assert result["success"]
    assert result["data"]["status"] == "renamed"
    assert Path(str(result["data"]["destination"])).name == "report.txt"
    assert (sandbox / "report.txt").read_text(encoding="utf-8") == "content"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX is case-sensitive; case-only is a plain rename.")
def test_case_only_rename_on_posix_is_plain_rename(config: Config, sandbox: Path) -> None:
    source = sandbox / "Report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "report.txt", config, dry_run=False)

    assert result["success"]
    assert not source.exists()
    assert (sandbox / "report.txt").read_text(encoding="utf-8") == "content"


# ---------------------------------------------------------------------------
# Audit ordering
# ---------------------------------------------------------------------------

def test_success_audit_records_planned_then_ok(config: Config, sandbox: Path) -> None:
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    rename_file(source, "renamed.txt", config, dry_run=False, audit=AuditLog(config.log_path))

    assert [entry["status"] for entry in _audit_entries(config)] == ["planned", "ok"]


def test_failed_audit_records_planned_then_failed(
    config: Config, sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    def locked_move(_source: Path, _destination: Path) -> None:
        raise PermissionError("source is locked")

    monkeypatch.setattr("agent.tools.rename_file._move_without_overwrite", locked_move)
    rename_file(source, "renamed.txt", config, dry_run=False)

    assert [entry["status"] for entry in _audit_entries(config)] == ["planned", "failed"]
    assert source.exists()


def test_dry_run_writes_planned_and_ok_with_dry_run_detail(
    config: Config, sandbox: Path
) -> None:
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    rename_file(source, "renamed.txt", config, audit=AuditLog(config.log_path))

    entries = _audit_entries(config)
    assert [entry["status"] for entry in entries] == ["planned", "ok"]
    assert entries[-1]["detail"] == "dry_run"
    assert source.exists()


def test_dry_run_writes_audit_per_adr_001(config: Config, sandbox: Path) -> None:
    """ADR-001 pin: dry_run=True with no explicit audit STILL writes audit.

    This replaces the previous `test_dry_run_does_not_create_audit_directory`
    which contradicted ADR-001. Contract:
      - AuditLog parent may be created.
      - Entries: planned, ok with detail == "dry_run".
      - Source file unchanged; destination not materialized.
    """
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    result = rename_file(source, "renamed.txt", config)

    assert result["success"] is True
    assert result["data"]["status"] == "would_rename"
    assert source.exists()
    assert not (sandbox / "renamed.txt").exists()

    # ADR-001: dry_run writes audit even without an explicit AuditLog argument.
    assert config.log_path.exists()
    entries = _audit_entries(config)
    assert [entry["status"] for entry in entries] == ["planned", "ok"]
    assert entries[-1]["detail"] == "dry_run"


def test_collision_race_retries_next_suffix_without_overwriting(
    config: Config, sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = sandbox / "report.txt"
    source.write_text("incoming", encoding="utf-8")
    (sandbox / "renamed.txt").write_text("original", encoding="utf-8")
    original_link = os.link
    raced = False

    def race(source_path: Path, destination_path: Path) -> None:
        nonlocal raced
        if not raced:
            raced = True
            destination_path.write_text("racer", encoding="utf-8")
            raise FileExistsError("destination became occupied")
        original_link(source_path, destination_path)

    monkeypatch.setattr("agent.tools.rename_file.os.link", race)
    result = rename_file(source, "renamed.txt", config, dry_run=False)

    assert result["success"]
    dest_name = Path(str(result["data"]["destination"])).name
    assert dest_name == "renamed (2).txt"
    assert (sandbox / "renamed (1).txt").read_text(encoding="utf-8") == "racer"
    assert (sandbox / "renamed (2).txt").read_text(encoding="utf-8") == "incoming"
    assert [entry["status"] for entry in _audit_entries(config)] == [
        "planned",
        "failed",
        "planned",
        "ok",
    ]


# ---------------------------------------------------------------------------
# Edge cases from task file
# ---------------------------------------------------------------------------

def test_empty_string_path_is_refused(config: Config, sandbox: Path) -> None:
    result = rename_file("", "renamed.txt", config)

    assert not result["success"]
    assert result["data"]["status"] == "skipped"


def test_trailing_separator_path_is_treated_as_file(
    config: Config, sandbox: Path
) -> None:
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")
    path_with_sep = str(source) + os.sep

    result = rename_file(path_with_sep, "renamed.txt", config, dry_run=False)

    assert result["success"]
    assert not source.exists()
    assert (sandbox / "renamed.txt").exists()


def test_no_infra_dir_created_by_real_rename(config: Config, sandbox: Path) -> None:
    """F-4 pin: real rename must not create infra dirs beyond the audit log file."""
    source = sandbox / "report.txt"
    source.write_text("content", encoding="utf-8")

    before = {p for p in sandbox.rglob("*")}
    rename_file(source, "renamed.txt", config, dry_run=False)
    after = {p for p in sandbox.rglob("*")}

    added = {p.name for p in after - before}
    # Only the audit log file itself (if log_path is inside sandbox) is allowed.
    assert added <= {"renamed.txt"} or all(
        p == config.log_path or config.log_path in p.parents for p in after - before
    )