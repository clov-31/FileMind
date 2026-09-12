"""Path validation — the last line of defence before anything touches disk.

Implements safety rules 4, 5, and 7 from CLAUDE.md: whitelist-not-blacklist,
hard-blocked system paths, and validate-before-executing. Every filesystem tool
routes through `validate_path` on both its source and its destination, including
paths that came from the agent's own rule engine — trust nothing.
"""

from __future__ import annotations

from pathlib import Path

from agent.core.config import Config

# Rejected regardless of the whitelist (safety rule 5). A user who lists one of
# these in WATCHED_FOLDERS gets a refusal, not access — the whitelist widens
# what is reachable, it never overrides a hard block.
HARD_BLOCKED: tuple[Path, ...] = (
    Path(r"C:\Windows"),
    Path(r"C:\Program Files"),
    Path(r"C:\Program Files (x86)"),
    Path(r"C:\ProgramData"),
)

# Matched as path components so they are caught anywhere, not just at the root.
HARD_BLOCKED_COMPONENTS: frozenset[str] = frozenset({"$recycle.bin", "system volume information"})

# AppData is the one qualified case in safety rule 5 — "anything under AppData
# *unless explicitly added*". So it is blocked by default, but a user who
# deliberately puts an AppData path in WATCHED_FOLDERS has opted in and gets it.
# Unlike the entries above, this is a default, not an absolute.
GUARDED_COMPONENT = "appdata"


def _appdata_opted_in(config: Config) -> bool:
    """True if the user explicitly whitelisted a path inside AppData."""
    return any(
        GUARDED_COMPONENT in {part.lower() for part in folder.parts}
        for folder in config.watched_folders
    )


def _is_within(child: Path, parent: Path) -> bool:
    """True if `child` is `parent` or sits underneath it."""
    try:
        return child == parent or child.is_relative_to(parent)
    except (OSError, ValueError):
        return False


def validate_path(path: Path | str, config: Config, *, must_exist: bool = True) -> tuple[bool, str]:
    """Check whether the agent is allowed to touch `path`.

    Returns `(allowed, reason)`. The reason explains a refusal in plain language
    so both the CLI and the audit log can report why something was blocked.

    Pass `must_exist=False` when validating a destination that has not been
    created yet. Resolution happens first, which collapses `..` segments and
    resolves symlinks — so a path that escapes the whitelist by either route is
    judged on where it actually lands, not on how it was spelled.
    """
    try:
        candidate = Path(path).expanduser().resolve()
    except (OSError, ValueError) as exc:
        return False, f"Path could not be resolved: {exc}"

    lowered_parts = {part.lower() for part in candidate.parts}
    blocked_component = lowered_parts & HARD_BLOCKED_COMPONENTS
    if blocked_component:
        name = sorted(blocked_component)[0]
        return False, f"Hard-blocked: path passes through '{name}'."

    for blocked in HARD_BLOCKED:
        if _is_within(candidate, blocked):
            return False, f"Hard-blocked system path: {blocked}"

    if GUARDED_COMPONENT in lowered_parts and not _appdata_opted_in(config):
        return False, (
            "Blocked: path passes through AppData. Add an AppData path to "
            "WATCHED_FOLDERS explicitly if you really want the agent in there."
        )

    if not any(_is_within(candidate, folder) for folder in config.watched_folders):
        allowed = ", ".join(str(f) for f in config.watched_folders)
        return False, f"Outside WATCHED_FOLDERS. Allowed: {allowed}"

    if must_exist and not candidate.exists():
        return False, f"Path does not exist: {candidate}"

    return True, "ok"


def assert_allowed(path: Path | str, config: Config, *, must_exist: bool = True) -> Path:
    """Validate `path` and return it resolved, raising `PermissionError` if not allowed.

    For call sites where a refusal is a programming error rather than something
    to report back to the user. Tool functions should prefer `validate_path` and
    return a structured failure instead of raising.
    """
    allowed, reason = validate_path(path, config, must_exist=must_exist)
    if not allowed:
        raise PermissionError(reason)
    return Path(path).expanduser().resolve()
