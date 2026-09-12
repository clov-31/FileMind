"""Classification: extension rules, and the guards around model output."""

from __future__ import annotations

from agent.core.classify import CATEGORY_NAMES, classify, classify_by_extension
from agent.core.llm import _parse_batch_response


def test_extension_map_covers_common_types() -> None:
    assert classify_by_extension("report.pdf") == "Documents"
    assert classify_by_extension("budget.xlsx") == "Spreadsheets"
    assert classify_by_extension("photo.JPG") == "Images"
    assert classify_by_extension("Claude Setup.exe") == "Installers"
    assert classify_by_extension("archive.zip") == "Archives"


def test_unknown_extension_returns_none() -> None:
    assert classify_by_extension("Ahok_HYB") is None
    assert classify_by_extension("data.qqq") is None


def test_classify_without_llm_falls_back_to_other() -> None:
    results = classify(["a.pdf", "mystery.qqq"], config=None, use_llm=False)
    assert [r.category for r in results] == ["Documents", "Other"]
    assert [r.tier for r in results] == ["rule", "rule"]


def test_classify_preserves_input_order() -> None:
    names = ["z.pdf", "a.png", "m.zip"]
    assert [r.name for r in classify(names, use_llm=False)] == names


def test_malformed_model_json_yields_nothing() -> None:
    """Garbage in must not raise; the caller then falls back to Other."""
    assert _parse_batch_response("not json at all", ["a.qqq"], CATEGORY_NAMES) == {}
    assert _parse_batch_response("", ["a.qqq"], CATEGORY_NAMES) == {}


def test_hallucinated_filenames_are_discarded() -> None:
    """A model that invents or 'corrects' a filename must not steer a move."""
    raw = '{"files": [{"name": "real.qqq", "category": "Documents"}, ' \
          '{"name": "invented.qqq", "category": "Documents"}]}'
    parsed = _parse_batch_response(raw, ["real.qqq"], CATEGORY_NAMES)
    assert parsed == {"real.qqq": "Documents"}


def test_invented_categories_are_discarded() -> None:
    raw = '{"files": [{"name": "a.qqq", "category": "Taxes"}]}'
    assert _parse_batch_response(raw, ["a.qqq"], CATEGORY_NAMES) == {}


def test_accepts_plain_mapping_shape() -> None:
    """Small models often answer with a bare object instead of the asked-for shape."""
    raw = '{"a.qqq": "Documents"}'
    assert _parse_batch_response(raw, ["a.qqq"], CATEGORY_NAMES) == {"a.qqq": "Documents"}
