"""Configuration loaded from `.env`.

Single source of truth for paths, model names, and thresholds. Nothing else in
the codebase hardcodes any of these — see the coding conventions in CLAUDE.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


class ConfigError(RuntimeError):
    """Raised at startup when `.env` is missing or unusable.

    Deliberately fatal: a misconfigured whitelist is a safety problem, not
    something to paper over with defaults.
    """


def _split_paths(raw: str) -> list[Path]:
    """Parse a comma-separated list of folder paths into resolved `Path`s."""
    return [Path(part.strip()).expanduser() for part in raw.split(",") if part.strip()]


@dataclass(frozen=True)
class Config:
    """Runtime configuration for the agent."""

    ollama_host: str
    ollama_model: str
    ollama_num_ctx: int
    watched_folders: list[Path]
    quarantine_folder: Path | None
    batch_confirm_threshold: int
    log_path: Path
    anthropic_api_key: str | None = field(default=None, repr=False)


def load_config(env_file: Path | None = None) -> Config:
    """Load and validate configuration from `.env`.

    Reads `.env` at the repo root unless `env_file` is given. Fails loudly
    rather than falling back to defaults for anything safety-relevant: an empty
    or nonexistent `WATCHED_FOLDERS` means the agent has no legal place to
    operate, which is an error, not an empty run.
    """
    env_path = env_file or (REPO_ROOT / ".env")
    if env_path.exists():
        load_dotenv(env_path, override=False)

    raw_watched = os.getenv("WATCHED_FOLDERS", "").strip()
    if not raw_watched:
        raise ConfigError(
            f"WATCHED_FOLDERS is empty. Copy env.example to {env_path} and set it "
            "to the folder(s) the agent is allowed to touch."
        )

    watched: list[Path] = []
    missing: list[Path] = []
    for folder in _split_paths(raw_watched):
        resolved = folder.resolve()
        if resolved.is_dir():
            watched.append(resolved)
        else:
            missing.append(folder)

    if missing:
        listed = ", ".join(str(p) for p in missing)
        raise ConfigError(f"WATCHED_FOLDERS contains paths that are not directories: {listed}")

    if not watched:
        raise ConfigError("WATCHED_FOLDERS resolved to no usable directories.")

    # Optional until a tool actually quarantines something. Safety rule 1 says
    # "delete" must mean "move to _Quarantine", but Phase 1 has no delete at
    # all, so requiring this would be a mandatory field with no consumer.
    quarantine_raw = os.getenv("QUARANTINE_FOLDER", "").strip()

    try:
        threshold = int(os.getenv("BATCH_CONFIRM_THRESHOLD", "5"))
    except ValueError as exc:
        raise ConfigError("BATCH_CONFIRM_THRESHOLD must be an integer.") from exc

    try:
        num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
    except ValueError as exc:
        raise ConfigError("OLLAMA_NUM_CTX must be an integer.") from exc

    model = os.getenv("OLLAMA_MODEL", "").strip()
    if not model:
        raise ConfigError("OLLAMA_MODEL is not set.")

    log_raw = os.getenv("LOG_PATH", "./logs/actions.log").strip()
    log_path = Path(log_raw)
    if not log_path.is_absolute():
        log_path = REPO_ROOT / log_path

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip() or None

    return Config(
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/"),
        ollama_model=model,
        ollama_num_ctx=num_ctx,
        watched_folders=watched,
        quarantine_folder=Path(quarantine_raw).expanduser() if quarantine_raw else None,
        batch_confirm_threshold=threshold,
        log_path=log_path,
        anthropic_api_key=api_key,
    )
