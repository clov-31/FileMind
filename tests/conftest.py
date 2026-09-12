"""Shared fixtures. Every test operates inside tmp_path — never real user files."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.core.config import Config


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """An empty watched folder."""
    folder = tmp_path / "Downloads"
    folder.mkdir()
    return folder


@pytest.fixture
def config(tmp_path: Path, sandbox: Path) -> Config:
    """A Config whose whitelist contains only the sandbox."""
    return Config(
        ollama_host="http://localhost:11434",
        ollama_model="llama3.1:8b",
        ollama_num_ctx=8192,
        watched_folders=[sandbox.resolve()],
        quarantine_folder=tmp_path / "_Quarantine",
        batch_confirm_threshold=5,
        log_path=tmp_path / "logs" / "actions.log",
    )


def make_files(folder: Path, names: list[str]) -> list[Path]:
    """Create empty files with the given names and return their paths."""
    created = []
    for name in names:
        path = folder / name
        path.write_text("x", encoding="utf-8")
        created.append(path)
    return created
