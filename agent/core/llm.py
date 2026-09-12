"""Ollama client for the local tier.

Two things this module refuses to do: trust the model's output, and let the
model's absence break a run. Every response is validated against the batch that
produced it, and an unreachable Ollama degrades the run to rules-only with a
single warning rather than raising.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Sequence

import requests

from agent.core.config import Config

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Small enough that a batch plus the system prompt sits well inside num_ctx,
# large enough that a folder of 150 files needs only a handful of calls.
BATCH_SIZE = 25
REQUEST_TIMEOUT = 120

_warned_unreachable = False


def load_prompt(name: str) -> str:
    """Read a versioned prompt from `agent/prompts/`."""
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def chat(
    messages: list[dict[str, str]],
    config: Config,
    *,
    json_mode: bool = False,
    timeout: int = REQUEST_TIMEOUT,
) -> str | None:
    """Send a chat request to Ollama and return the assistant's text.

    Returns None if Ollama is unreachable or answers with an error — callers are
    expected to degrade rather than fail. `num_ctx` is always set explicitly:
    Ollama silently defaults to a 4K window regardless of the model's real
    maximum, which truncates long prompts with no warning at all.
    """
    global _warned_unreachable

    payload: dict[str, Any] = {
        "model": config.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {"num_ctx": config.ollama_num_ctx, "temperature": 0},
    }
    if json_mode:
        payload["format"] = "json"

    try:
        response = requests.post(
            f"{config.ollama_host}/api/chat", json=payload, timeout=timeout
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")
    except (requests.RequestException, ValueError) as exc:
        if not _warned_unreachable:
            print(
                f"[llm] Ollama unavailable at {config.ollama_host} ({exc}). "
                "Continuing with rule-based classification only.",
                file=sys.stderr,
            )
            _warned_unreachable = True
        return None


def _parse_batch_response(
    raw: str, batch: Sequence[str], valid_categories: Sequence[str]
) -> dict[str, str]:
    """Extract filename -> category pairs from one model response.

    Discards anything that does not survive validation: unparseable JSON, a
    filename the model was never given (a hallucination, or a "helpfully"
    corrected spelling that no longer matches a real file), or a category
    outside the allowed set. Dropped entries fall back to `Other` upstream.
    """
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}

    if isinstance(parsed, dict) and isinstance(parsed.get("files"), list):
        items = parsed["files"]
    elif isinstance(parsed, list):
        items = parsed
    elif isinstance(parsed, dict):
        items = [{"name": k, "category": v} for k, v in parsed.items()]
    else:
        return {}

    allowed = set(valid_categories)
    in_batch = set(batch)
    result: dict[str, str] = {}

    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("filename")
        category = item.get("category")
        if not isinstance(name, str) or not isinstance(category, str):
            continue
        if name not in in_batch or category not in allowed:
            continue
        result[name] = category

    return result


def classify_unknown_files(
    filenames: list[str], config: Config, valid_categories: Sequence[str]
) -> dict[str, str]:
    """Ask the local model to categorise files the extension rules could not.

    Processes filenames in batches and returns only the answers that passed
    validation. A filename absent from the returned mapping was either
    unanswered or answered invalidly; either way the caller treats it as `Other`.
    Never raises.
    """
    if not filenames:
        return {}

    try:
        system_prompt = load_prompt("classify_files.md")
    except OSError as exc:
        print(f"[llm] could not read classification prompt: {exc}", file=sys.stderr)
        return {}

    categories_line = ", ".join(valid_categories)
    answers: dict[str, str] = {}

    for start in range(0, len(filenames), BATCH_SIZE):
        batch = filenames[start : start + BATCH_SIZE]
        user_content = (
            f"Allowed categories: {categories_line}\n\n"
            "Classify each of these filenames:\n"
            + "\n".join(f"- {name}" for name in batch)
        )
        raw = chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            config,
            json_mode=True,
        )
        if raw is None:
            break  # Ollama is down; stop trying and let everything fall back.
        answers.update(_parse_batch_response(raw, batch, valid_categories))

    return answers
