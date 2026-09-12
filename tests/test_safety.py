"""Safety rules 4, 5, 7 — the checks that stand between the agent and the disk."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from agent.core.config import Config
from agent.core.safety import validate_path


def test_path_inside_watched_folder_is_allowed(config: Config, sandbox: Path) -> None:
    target = sandbox / "report.pdf"
    target.write_text("x", encoding="utf-8")
    allowed, reason = validate_path(target, config)
    assert allowed, reason


def test_path_outside_watched_folders_is_rejected(config: Config, tmp_path: Path) -> None:
    outsider = tmp_path / "elsewhere"
    outsider.mkdir()
    allowed, reason = validate_path(outsider, config)
    assert not allowed
    assert "Outside WATCHED_FOLDERS" in reason


def test_parent_traversal_cannot_escape_the_whitelist(config: Config, sandbox: Path) -> None:
    """`..` is collapsed by resolution, so escaping by spelling does not work."""
    escaped = sandbox / ".." / "secrets.txt"
    allowed, reason = validate_path(escaped, config, must_exist=False)
    assert not allowed
    assert "Outside WATCHED_FOLDERS" in reason


def test_hard_blocked_path_rejected_even_when_whitelisted(config: Config) -> None:
    """Safety rule 5: a hard block outranks the whitelist, always."""
    windows = Path(r"C:\Windows")
    permissive = dataclasses.replace(config, watched_folders=[windows])
    allowed, reason = validate_path(windows / "System32", permissive, must_exist=False)
    assert not allowed
    assert "Hard-blocked" in reason


def test_appdata_is_blocked_by_default(config: Config) -> None:
    """Safety rule 5 blocks AppData unless the user explicitly whitelists it."""
    elsewhere = dataclasses.replace(config, watched_folders=[Path(r"C:\Watched")])
    allowed, reason = validate_path(
        Path(r"C:\Watched\AppData\thing.txt"), elsewhere, must_exist=False
    )
    assert not allowed
    assert "appdata" in reason.lower()


def test_appdata_reachable_when_explicitly_whitelisted(config: Config) -> None:
    """"...unless explicitly added" — an opted-in AppData path is reachable."""
    opted_in = dataclasses.replace(
        config, watched_folders=[Path(r"C:\Users\someone\AppData\Local\MyStuff")]
    )
    allowed, reason = validate_path(
        Path(r"C:\Users\someone\AppData\Local\MyStuff\file.txt"), opted_in, must_exist=False
    )
    assert allowed, reason


def test_missing_path_rejected_when_existence_required(config: Config, sandbox: Path) -> None:
    allowed, _ = validate_path(sandbox / "nope.txt", config)
    assert not allowed

    allowed, _ = validate_path(sandbox / "nope.txt", config, must_exist=False)
    assert allowed, "destinations that do not exist yet must be allowed"
