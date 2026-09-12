"""File classification: deterministic rules first, local model only for leftovers.

The extension map is the primary classifier, not a fallback. It settles the
category for the large majority of a typical Downloads folder without any model
involvement, which means the pipeline works with Ollama stopped and stays fast
and repeatable. The model is consulted only for extensions the map does not
know, and its answers are validated before use — see `agent/core/llm.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from agent.core.config import Config

OTHER = "Other"

# Category -> extensions. Lowercase, leading dot. Order does not matter; each
# extension belongs to exactly one category.
CATEGORY_EXTENSIONS: dict[str, frozenset[str]] = {
    "Documents": frozenset({".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".odt", ".pptx", ".ppt"}),
    "Spreadsheets": frozenset({".xlsx", ".xls", ".csv"}),
    "Images": frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".heic"}),
    "Video": frozenset({".mp4", ".mkv", ".mov", ".avi", ".webm"}),
    "Audio": frozenset({".mp3", ".wav", ".m4a", ".flac"}),
    "Installers": frozenset({".exe", ".msi"}),
    "Archives": frozenset({".zip", ".rar", ".7z", ".tar", ".gz"}),
    "Code": frozenset({".py", ".js", ".ts", ".json", ".html", ".css", ".ipynb"}),
}

# Every folder name the agent may create. The scanner uses this to skip its own
# output so repeat runs are idempotent.
CATEGORY_NAMES: tuple[str, ...] = (*CATEGORY_EXTENSIONS.keys(), OTHER)

_EXTENSION_TO_CATEGORY: dict[str, str] = {
    ext: category for category, exts in CATEGORY_EXTENSIONS.items() for ext in exts
}


class Classification(NamedTuple):
    """One file's category and which tier decided it."""

    name: str
    category: str
    tier: str  # "rule" | "local" | "cloud"


def classify_by_extension(filename: str) -> str | None:
    """Return the category for a filename's extension, or None if unknown.

    Unknown means "no rule covers this", which is the signal to escalate to the
    local model — not an error.
    """
    ext = Path(filename).suffix.lower()
    return _EXTENSION_TO_CATEGORY.get(ext)


def classify(
    filenames: list[str],
    config: "Config | None" = None,
    *,
    use_llm: bool = True,
) -> list[Classification]:
    """Classify filenames into destination categories.

    Applies the extension map to everything first. Whatever is left over goes to
    the local model in batches, if `use_llm` is set and a config was supplied.
    Anything the model cannot classify — or every file, if the model is
    unreachable — falls back to `Other`, which is a real destination folder, not
    a failure state.
    """
    results: dict[str, Classification] = {}
    unknown: list[str] = []

    for name in filenames:
        category = classify_by_extension(name)
        if category is not None:
            results[name] = Classification(name, category, "rule")
        else:
            unknown.append(name)

    if unknown and use_llm and config is not None:
        from agent.core.llm import classify_unknown_files

        model_answers = classify_unknown_files(unknown, config, valid_categories=CATEGORY_NAMES)
        for name in unknown:
            category = model_answers.get(name)
            if category:
                results[name] = Classification(name, category, "local")

    for name in unknown:
        results.setdefault(name, Classification(name, OTHER, "rule"))

    return [results[name] for name in filenames]
