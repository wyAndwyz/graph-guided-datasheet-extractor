"""Select relevant pages based on page score comparison results.

This module selects pages after rule-based and LLM-based page scoring.

Input:
    outputs/intermediate/page_score_comparison.json

Output:
    outputs/intermediate/selected_pages.json

Supported selection strategies:

1. union
   Select a page if either rule-based or LLM-based scorer selects it.

2. intersection
   Select a page only if both scorers select it.

3. hybrid
   Recommended default.
   - primary: both methods select the page
   - secondary: only one method selects the page
   - discarded: neither method selects the page

The hybrid strategy keeps both primary and secondary pages in the output,
but labels them separately so downstream steps can decide whether to use
only primary pages or include secondary pages as fallback context.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal


SelectionStrategy = Literal["union", "intersection", "hybrid"]
SelectionStatus = Literal["selected", "selected_primary", "selected_secondary", "discarded"]


@dataclass(frozen=True)
class SelectedPage:
    """Selected or discarded page with decision metadata."""

    page_number: int
    selection_status: SelectionStatus
    selected_for_extraction: bool
    selection_strategy: str

    rule_based_selected: bool
    rule_based_level: str
    rule_based_score: float
    rule_based_rank: int

    llm_selected: bool
    llm_level: str
    llm_score: float
    llm_rank: int
    llm_useful_for_extraction: bool
    llm_likely_content_type: str

    agreement_on_selection: bool
    agreement_on_level: bool
    decision_reason: str


@dataclass(frozen=True)
class PageSelectionSummary:
    """Summary of selected pages."""

    strategy: str
    page_count: int
    selected_page_count: int
    discarded_page_count: int
    selected_pages: list[int]
    selected_primary_pages: list[int]
    selected_secondary_pages: list[int]
    discarded_pages: list[int]


@dataclass(frozen=True)
class PageSelectionResult:
    """Full page selection result."""

    selection_method: str
    source_file: str
    summary: PageSelectionSummary
    pages: list[SelectedPage]


class PageSelectionError(RuntimeError):
    """Raised when page selection fails."""


def load_page_score_comparison_json(input_path: str | Path) -> dict[str, Any]:
    """Load page score comparison JSON."""

    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Page score comparison JSON not found: {input_path}")

    try:
        return json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PageSelectionError(f"Invalid JSON file: {input_path}") from exc


def _validate_strategy(strategy: str) -> SelectionStrategy:
    """Validate and normalize selection strategy."""

    normalized = strategy.strip().lower()

    if normalized not in {"union", "intersection", "hybrid"}:
        raise PageSelectionError(
            "Unsupported selection strategy. "
            "Expected one of: union, intersection, hybrid. "
            f"Got: {strategy}"
        )

    return normalized  # type: ignore[return-value]


def _get_source_file(comparison_payload: dict[str, Any]) -> str:
    """Get source file from comparison summary."""

    summary = comparison_payload.get("summary", {})

    if not isinstance(summary, dict):
        return ""

    rule_source = str(summary.get("rule_based_source_file", ""))
    llm_source = str(summary.get("llm_based_source_file", ""))

    if rule_source and rule_source == llm_source:
        return rule_source

    if rule_source:
        return rule_source

    return llm_source


def _select_page_union(page: dict[str, Any]) -> tuple[SelectionStatus, bool, str]:
    """Select page using union strategy."""

    rule_selected = bool(page.get("rule_based_selected", False))
    llm_selected = bool(page.get("llm_selected", False))

    if rule_selected or llm_selected:
        if rule_selected and llm_selected:
            reason = "Selected because both scorers selected this page."
        elif rule_selected:
            reason = "Selected because the rule-based scorer selected this page."
        else:
            reason = "Selected because the LLM-based scorer selected this page."

        return "selected", True, reason

    return "discarded", False, "Discarded because neither scorer selected this page."


def _select_page_intersection(page: dict[str, Any]) -> tuple[SelectionStatus, bool, str]:
    """Select page using intersection strategy."""

    rule_selected = bool(page.get("rule_based_selected", False))
    llm_selected = bool(page.get("llm_selected", False))

    if rule_selected and llm_selected:
        return "selected", True, "Selected because both scorers selected this page."

    if rule_selected and not llm_selected:
        return (
            "discarded",
            False,
            "Discarded because only the rule-based scorer selected this page.",
        )

    if llm_selected and not rule_selected:
        return (
            "discarded",
            False,
            "Discarded because only the LLM-based scorer selected this page.",
        )

    return "discarded", False, "Discarded because neither scorer selected this page."


def _select_page_hybrid(page: dict[str, Any]) -> tuple[SelectionStatus, bool, str]:
    """Select page using hybrid strategy.

    Hybrid strategy:
    - selected_primary: both scorers select the page
    - selected_secondary: only one scorer selects the page
    - discarded: neither scorer selects the page
    """

    rule_selected = bool(page.get("rule_based_selected", False))
    llm_selected = bool(page.get("llm_selected", False))

    if rule_selected and llm_selected:
        return (
            "selected_primary",
            True,
            "Selected as primary because both scorers selected this page.",
        )

    if rule_selected and not llm_selected:
        return (
            "selected_secondary",
            True,
            "Selected as secondary because only the rule-based scorer selected this page.",
        )

    if llm_selected and not rule_selected:
        return (
            "selected_secondary",
            True,
            "Selected as secondary because only the LLM-based scorer selected this page.",
        )

    return "discarded", False, "Discarded because neither scorer selected this page."


def _select_single_page(
    page: dict[str, Any],
    strategy: SelectionStrategy,
) -> SelectedPage:
    """Select or discard one page according to the chosen strategy."""

    if strategy == "union":
        selection_status, selected_for_extraction, reason = _select_page_union(page)
    elif strategy == "intersection":
        selection_status, selected_for_extraction, reason = _select_page_intersection(page)
    elif strategy == "hybrid":
        selection_status, selected_for_extraction, reason = _select_page_hybrid(page)
    else:  # pragma: no cover - protected by _validate_strategy
        raise PageSelectionError(f"Unsupported strategy: {strategy}")

    return SelectedPage(
        page_number=int(page["page_number"]),
        selection_status=selection_status,
        selected_for_extraction=selected_for_extraction,
        selection_strategy=strategy,
        rule_based_selected=bool(page.get("rule_based_selected", False)),
        rule_based_level=str(page.get("rule_based_level", "")),
        rule_based_score=float(page.get("rule_based_score", 0.0)),
        rule_based_rank=int(page.get("rule_based_rank", 0)),
        llm_selected=bool(page.get("llm_selected", False)),
        llm_level=str(page.get("llm_level", "")),
        llm_score=float(page.get("llm_score", 0.0)),
        llm_rank=int(page.get("llm_rank", 0)),
        llm_useful_for_extraction=bool(page.get("llm_useful_for_extraction", False)),
        llm_likely_content_type=str(page.get("llm_likely_content_type", "")),
        agreement_on_selection=bool(page.get("agreement_on_selection", False)),
        agreement_on_level=bool(page.get("agreement_on_level", False)),
        decision_reason=reason,
    )


def select_pages_from_comparison(
    comparison_payload: dict[str, Any],
    strategy: str = "hybrid",
) -> PageSelectionResult:
    """Select pages from a page score comparison payload.

    Args:
        comparison_payload: Parsed page_score_comparison.json payload.
        strategy: Selection strategy: union, intersection, or hybrid.

    Returns:
        PageSelectionResult.
    """

    normalized_strategy = _validate_strategy(strategy)

    pages_payload = comparison_payload.get("pages", [])

    if not isinstance(pages_payload, list):
        raise PageSelectionError("Expected 'pages' to be a list in comparison payload.")

    selected_pages = [
        _select_single_page(page, normalized_strategy)
        for page in pages_payload
    ]

    selected_page_numbers = [
        page.page_number for page in selected_pages if page.selected_for_extraction
    ]

    discarded_page_numbers = [
        page.page_number for page in selected_pages if not page.selected_for_extraction
    ]

    selected_primary_pages = [
        page.page_number
        for page in selected_pages
        if page.selection_status in {"selected", "selected_primary"}
    ]

    selected_secondary_pages = [
        page.page_number
        for page in selected_pages
        if page.selection_status == "selected_secondary"
    ]

    summary = PageSelectionSummary(
        strategy=normalized_strategy,
        page_count=len(selected_pages),
        selected_page_count=len(selected_page_numbers),
        discarded_page_count=len(discarded_page_numbers),
        selected_pages=selected_page_numbers,
        selected_primary_pages=selected_primary_pages,
        selected_secondary_pages=selected_secondary_pages,
        discarded_pages=discarded_page_numbers,
    )

    return PageSelectionResult(
        selection_method=f"page_selection_{normalized_strategy}_v1",
        source_file=_get_source_file(comparison_payload),
        summary=summary,
        pages=selected_pages,
    )


def page_selection_result_to_dict(result: PageSelectionResult) -> dict[str, Any]:
    """Convert page selection result to a JSON-serializable dictionary."""

    return {
        "selection_method": result.selection_method,
        "source_file": result.source_file,
        "summary": asdict(result.summary),
        "pages": [asdict(page) for page in result.pages],
    }


def write_selected_pages_json(
    result: PageSelectionResult,
    output_path: str | Path,
) -> Path:
    """Write selected pages JSON."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(page_selection_result_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def select_pages_from_comparison_file(
    input_path: str | Path,
    output_path: str | Path,
    strategy: str = "hybrid",
) -> Path:
    """Convenience function: select pages from comparison JSON and write output."""

    payload = load_page_score_comparison_json(input_path)
    result = select_pages_from_comparison(payload, strategy=strategy)
    return write_selected_pages_json(result, output_path)