"""Compare rule-based and LLM-based page scoring results.

This module compares two Phase 2 screening outputs:

    outputs/intermediate/page_scores_rule_based.json
    outputs/intermediate/page_scores_llm_based.json

and writes:

    outputs/intermediate/page_score_comparison.json

The comparison focuses on:
- page-level score differences;
- relevance-level agreement;
- selection agreement;
- ranking agreement;
- disagreement cases for later inspection.

Important:
The numeric score scales are different:
- rule-based score is a weighted accumulated rule score;
- LLM-based score is a 0-100 relevance score.

Therefore, this comparator does not assume that raw numeric scores are directly
comparable. It mainly compares levels, ranking, and selected/not-selected status.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SELECTED_LEVELS = {"high", "medium"}


@dataclass(frozen=True)
class PageScoreComparison:
    """Comparison result for one page."""

    page_number: int

    rule_based_score: float
    rule_based_level: str
    rule_based_selected: bool
    rule_based_rank: int

    llm_score: float
    llm_level: str
    llm_selected: bool
    llm_rank: int
    llm_useful_for_extraction: bool
    llm_likely_content_type: str

    agreement_on_level: bool
    agreement_on_selection: bool
    rank_difference: int
    score_difference_raw: float

    rule_based_matched_categories: list[str]
    llm_extraction_targets_found: list[str]

    comparison_note: str


@dataclass(frozen=True)
class PageScoreComparisonSummary:
    """Overall comparison summary."""

    page_count: int
    same_source_file: bool
    rule_based_source_file: str
    llm_based_source_file: str
    agreement_on_level_count: int
    agreement_on_selection_count: int
    disagreement_on_level_count: int
    disagreement_on_selection_count: int
    pages_with_level_disagreement: list[int]
    pages_with_selection_disagreement: list[int]
    rule_based_selected_pages: list[int]
    llm_based_selected_pages: list[int]
    intersection_selected_pages: list[int]
    rule_only_selected_pages: list[int]
    llm_only_selected_pages: list[int]


@dataclass(frozen=True)
class PageScoreComparisonResult:
    """Full comparison result between rule-based and LLM-based scoring."""

    comparison_method: str
    summary: PageScoreComparisonSummary
    pages: list[PageScoreComparison]


class PageScoreComparisonError(RuntimeError):
    """Raised when page score comparison fails."""


def load_json_file(input_path: str | Path) -> dict[str, Any]:
    """Load a JSON file."""

    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"JSON file not found: {input_path}")

    try:
        return json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PageScoreComparisonError(f"Invalid JSON file: {input_path}") from exc


def _index_pages_by_number(payload: dict[str, Any], label: str) -> dict[int, dict[str, Any]]:
    """Create a page-number index from a page scoring payload."""

    pages = payload.get("pages", [])

    if not isinstance(pages, list):
        raise PageScoreComparisonError(f"Expected 'pages' to be a list in {label} payload.")

    page_index: dict[int, dict[str, Any]] = {}

    for page in pages:
        if "page_number" not in page:
            raise PageScoreComparisonError(
                f"Missing 'page_number' in {label} page entry: {page}"
            )

        page_number = int(page["page_number"])

        if page_number in page_index:
            raise PageScoreComparisonError(
                f"Duplicate page_number {page_number} in {label} payload."
            )

        page_index[page_number] = page

    return page_index


def _rank_pages_by_score(page_index: dict[int, dict[str, Any]]) -> dict[int, int]:
    """Rank pages by descending score.

    Rank starts at 1. Ties are resolved by page number to keep output deterministic.
    """

    sorted_pages = sorted(
        page_index.values(),
        key=lambda page: (-float(page.get("score", 0.0)), int(page["page_number"])),
    )

    return {
        int(page["page_number"]): rank
        for rank, page in enumerate(sorted_pages, start=1)
    }


def _is_selected_by_level(level: str) -> bool:
    """Return whether a relevance level means the page is selected."""

    return level in SELECTED_LEVELS


def _build_comparison_note(
    rule_level: str,
    llm_level: str,
    rule_selected: bool,
    llm_selected: bool,
    rank_difference: int,
) -> str:
    """Build a short human-readable note for one page comparison."""

    if rule_selected == llm_selected and rule_level == llm_level:
        return "Both methods agree on relevance level and selection."

    if rule_selected == llm_selected and rule_level != llm_level:
        return (
            "Both methods agree on selection, but assign different relevance levels."
        )

    if rule_selected and not llm_selected:
        return "Rule-based scorer selects this page, but LLM-based scorer does not."

    if llm_selected and not rule_selected:
        return "LLM-based scorer selects this page, but rule-based scorer does not."

    if abs(rank_difference) >= 2:
        return "Both methods disagree noticeably on ranking."

    return "Minor disagreement between scoring methods."


def compare_page_scores(
    rule_based_payload: dict[str, Any],
    llm_based_payload: dict[str, Any],
) -> PageScoreComparisonResult:
    """Compare rule-based and LLM-based page scoring payloads."""

    rule_source_file = str(rule_based_payload.get("source_file", ""))
    llm_source_file = str(llm_based_payload.get("source_file", ""))

    rule_pages = _index_pages_by_number(rule_based_payload, label="rule-based")
    llm_pages = _index_pages_by_number(llm_based_payload, label="LLM-based")

    rule_page_numbers = set(rule_pages.keys())
    llm_page_numbers = set(llm_pages.keys())

    if rule_page_numbers != llm_page_numbers:
        missing_in_rule = sorted(llm_page_numbers - rule_page_numbers)
        missing_in_llm = sorted(rule_page_numbers - llm_page_numbers)
        raise PageScoreComparisonError(
            "Page sets do not match. "
            f"Missing in rule-based: {missing_in_rule}; "
            f"missing in LLM-based: {missing_in_llm}"
        )

    rule_ranks = _rank_pages_by_score(rule_pages)
    llm_ranks = _rank_pages_by_score(llm_pages)

    page_comparisons: list[PageScoreComparison] = []

    for page_number in sorted(rule_page_numbers):
        rule_page = rule_pages[page_number]
        llm_page = llm_pages[page_number]

        rule_score = float(rule_page.get("score", 0.0))
        llm_score = float(llm_page.get("score", 0.0))

        rule_level = str(rule_page.get("relevance_level", ""))
        llm_level = str(llm_page.get("relevance_level", ""))

        rule_selected = _is_selected_by_level(rule_level)
        llm_selected = _is_selected_by_level(llm_level)

        rule_rank = rule_ranks[page_number]
        llm_rank = llm_ranks[page_number]
        rank_difference = rule_rank - llm_rank

        agreement_on_level = rule_level == llm_level
        agreement_on_selection = rule_selected == llm_selected

        comparison_note = _build_comparison_note(
            rule_level=rule_level,
            llm_level=llm_level,
            rule_selected=rule_selected,
            llm_selected=llm_selected,
            rank_difference=rank_difference,
        )

        page_comparisons.append(
            PageScoreComparison(
                page_number=page_number,
                rule_based_score=round(rule_score, 2),
                rule_based_level=rule_level,
                rule_based_selected=rule_selected,
                rule_based_rank=rule_rank,
                llm_score=round(llm_score, 2),
                llm_level=llm_level,
                llm_selected=llm_selected,
                llm_rank=llm_rank,
                llm_useful_for_extraction=bool(
                    llm_page.get("useful_for_extraction", False)
                ),
                llm_likely_content_type=str(
                    llm_page.get("likely_content_type", "")
                ),
                agreement_on_level=agreement_on_level,
                agreement_on_selection=agreement_on_selection,
                rank_difference=rank_difference,
                score_difference_raw=round(llm_score - rule_score, 2),
                rule_based_matched_categories=list(
                    rule_page.get("matched_categories", [])
                ),
                llm_extraction_targets_found=list(
                    llm_page.get("extraction_targets_found", [])
                ),
                comparison_note=comparison_note,
            )
        )

    agreement_on_level_pages = [
        page.page_number for page in page_comparisons if page.agreement_on_level
    ]
    agreement_on_selection_pages = [
        page.page_number for page in page_comparisons if page.agreement_on_selection
    ]

    pages_with_level_disagreement = [
        page.page_number for page in page_comparisons if not page.agreement_on_level
    ]
    pages_with_selection_disagreement = [
        page.page_number for page in page_comparisons if not page.agreement_on_selection
    ]

    rule_selected_pages = [
        page.page_number for page in page_comparisons if page.rule_based_selected
    ]
    llm_selected_pages = [
        page.page_number for page in page_comparisons if page.llm_selected
    ]

    rule_selected_set = set(rule_selected_pages)
    llm_selected_set = set(llm_selected_pages)

    summary = PageScoreComparisonSummary(
        page_count=len(page_comparisons),
        same_source_file=rule_source_file == llm_source_file,
        rule_based_source_file=rule_source_file,
        llm_based_source_file=llm_source_file,
        agreement_on_level_count=len(agreement_on_level_pages),
        agreement_on_selection_count=len(agreement_on_selection_pages),
        disagreement_on_level_count=len(pages_with_level_disagreement),
        disagreement_on_selection_count=len(pages_with_selection_disagreement),
        pages_with_level_disagreement=pages_with_level_disagreement,
        pages_with_selection_disagreement=pages_with_selection_disagreement,
        rule_based_selected_pages=rule_selected_pages,
        llm_based_selected_pages=llm_selected_pages,
        intersection_selected_pages=sorted(rule_selected_set & llm_selected_set),
        rule_only_selected_pages=sorted(rule_selected_set - llm_selected_set),
        llm_only_selected_pages=sorted(llm_selected_set - rule_selected_set),
    )

    return PageScoreComparisonResult(
        comparison_method="rule_based_vs_llm_based_v1",
        summary=summary,
        pages=page_comparisons,
    )


def comparison_result_to_dict(result: PageScoreComparisonResult) -> dict[str, Any]:
    """Convert comparison result to a JSON-serializable dictionary."""

    return {
        "comparison_method": result.comparison_method,
        "summary": asdict(result.summary),
        "pages": [asdict(page) for page in result.pages],
    }


def write_page_score_comparison_json(
    result: PageScoreComparisonResult,
    output_path: str | Path,
) -> Path:
    """Write page score comparison result to JSON."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(comparison_result_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def compare_page_score_files(
    rule_based_input_path: str | Path,
    llm_based_input_path: str | Path,
    output_path: str | Path,
) -> Path:
    """Convenience function: compare two page score files and write JSON output."""

    rule_payload = load_json_file(rule_based_input_path)
    llm_payload = load_json_file(llm_based_input_path)

    result = compare_page_scores(
        rule_based_payload=rule_payload,
        llm_based_payload=llm_payload,
    )

    return write_page_score_comparison_json(result, output_path)