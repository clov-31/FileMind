"""scan_folder: what it reports, and what it deliberately ignores."""

from __future__ import annotations

from pathlib import Path

from agent.core.config import Config
from agent.tools.scan_folder import scan_folder
from tests.conftest import make_files


def test_lists_loose_files(config: Config, sandbox: Path) -> None:
    make_files(sandbox, ["a.pdf", "b.png", "c.zip"])
    result = scan_folder(sandbox, config)
    assert result["success"]
    assert {f["name"] for f in result["data"]["files"]} == {"a.pdf", "b.png", "c.zip"}


def test_directories_are_skipped_not_moved(config: Config, sandbox: Path) -> None:
    """Real folders like Downloads/Apps must be left entirely alone."""
    (sandbox / "Apps").mkdir()
    make_files(sandbox, ["a.pdf"])

    result = scan_folder(sandbox, config)
    assert [f["name"] for f in result["data"]["files"]] == ["a.pdf"]
    assert result["data"]["skipped"]["directories"] == 1


def test_agent_destination_folders_are_skipped(config: Config, sandbox: Path) -> None:
    """This is what makes a second run idempotent instead of re-filing everything."""
    (sandbox / "Documents").mkdir()
    (sandbox / "Images").mkdir()
    (sandbox / "_Quarantine").mkdir()

    result = scan_folder(sandbox, config)
    assert result["data"]["files"] == []
    assert result["data"]["skipped"]["agent_folders"] == 3
    assert result["data"]["skipped"]["directories"] == 0


def test_in_progress_downloads_are_skipped(config: Config, sandbox: Path) -> None:
    make_files(sandbox, ["done.pdf", "half.crdownload", "partial.part", "temp.tmp"])
    result = scan_folder(sandbox, config)
    assert [f["name"] for f in result["data"]["files"]] == ["done.pdf"]
    assert result["data"]["skipped"]["in_progress"] == 3


def test_dotfiles_are_skipped(config: Config, sandbox: Path) -> None:
    make_files(sandbox, [".gitignore", "real.pdf"])
    result = scan_folder(sandbox, config)
    assert [f["name"] for f in result["data"]["files"]] == ["real.pdf"]
    assert result["data"]["skipped"]["hidden"] == 1


def test_scanning_outside_the_whitelist_is_refused(config: Config, tmp_path: Path) -> None:
    outsider = tmp_path / "not_watched"
    outsider.mkdir()
    result = scan_folder(outsider, config)
    assert not result["success"]
    assert "Refused" in result["message"]


def test_nested_files_are_not_reached(config: Config, sandbox: Path) -> None:
    """Phase 1 is top-level only."""
    nested = sandbox / "Apps"
    nested.mkdir()
    make_files(nested, ["deep.pdf"])

    result = scan_folder(sandbox, config)
    assert result["data"]["files"] == []
