# $env:PYTHONPATH="src"
# python -m graph_datasheet_extractor.preprocessing.main_select_pages --strategy hybrid
# python -m graph_datasheet_extractor.preprocessing.main_select_pages --strategy union
# python -m graph_datasheet_extractor.preprocessing.main_select_pages --strategy intersection

"""Command-line entry point for selecting pages after score comparison.

Run from the repository root with:

    python -m graph_datasheet_extractor.preprocessing.main_select_pages

Default input:

    outputs/intermediate/page_score_comparison.json

Default output:

    outputs/intermediate/selected_pages.json

Supported strategies:

    union
    intersection
    hybrid

Examples:

    python -m graph_datasheet_extractor.preprocessing.main_select_pages --strategy hybrid

    python -m graph_datasheet_extractor.preprocessing.main_select_pages --strategy union

    python -m graph_datasheet_extractor.preprocessing.main_select_pages --strategy intersection
"""

from __future__ import annotations

import argparse
from pathlib import Path

from graph_datasheet_extractor.preprocessing.page_selector import (
    PageSelectionError,
    load_page_score_comparison_json,
    select_pages_from_comparison,
    write_selected_pages_json,
)


DEFAULT_INPUT_JSON = Path("outputs/intermediate/page_score_comparison.json")
DEFAULT_OUTPUT_JSON = Path("outputs/intermediate/selected_pages.json")
DEFAULT_STRATEGY = "hybrid"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Select relevant pages using union, intersection, or hybrid strategy."
    )

    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_INPUT_JSON,
        help=f"Path to page_score_comparison.json. Default: {DEFAULT_INPUT_JSON}",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help=f"Path to selected_pages.json. Default: {DEFAULT_OUTPUT_JSON}",
    )

    parser.add_argument(
        "--strategy",
        "-s",
        type=str,
        default=DEFAULT_STRATEGY,
        choices=["union", "intersection", "hybrid"],
        help=(
            "Page selection strategy. "
            "union = selected by either scorer; "
            "intersection = selected by both scorers; "
            "hybrid = primary if both selected, secondary if only one selected. "
            f"Default: {DEFAULT_STRATEGY}"
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Select pages from page score comparison JSON."""

    args = parse_args()

    input_json: Path = args.input
    output_json: Path = args.output
    strategy: str = args.strategy

    print("=== Page Selection ===")
    print(f"Input JSON : {input_json}")
    print(f"Output JSON: {output_json}")
    print(f"Strategy   : {strategy}")
    print()

    try:
        comparison_payload = load_page_score_comparison_json(input_json)
        result = select_pages_from_comparison(
            comparison_payload=comparison_payload,
            strategy=strategy,
        )
        write_selected_pages_json(result, output_json)

    except FileNotFoundError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except PageSelectionError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    summary = result.summary

    print("Result: PASSED")
    print()
    print("Selection summary:")
    print(f"- Source file             : {result.source_file}")
    print(f"- Strategy                : {summary.strategy}")
    print(f"- Pages evaluated          : {summary.page_count}")
    print(f"- Selected page count      : {summary.selected_page_count}")
    print(f"- Discarded page count     : {summary.discarded_page_count}")
    print(f"- Selected pages           : {summary.selected_pages}")
    print(f"- Selected primary pages   : {summary.selected_primary_pages}")
    print(f"- Selected secondary pages : {summary.selected_secondary_pages}")
    print(f"- Discarded pages          : {summary.discarded_pages}")
    print()
    print("Per-page decision:")

    for page in result.pages:
        print(
            f"- Page {page.page_number}: "
            f"status={page.selection_status}, "
            f"selected={page.selected_for_extraction}, "
            f"rule={page.rule_based_level}({page.rule_based_score}), "
            f"llm={page.llm_level}({page.llm_score}), "
            f"reason={page.decision_reason}"
        )

    print()
    print(f"Written to: {output_json}")


if __name__ == "__main__":
    main()
