# $env:PYTHONPATH="src"
# python -m graph_datasheet_extractor.preprocessing.main_score_pages_rule_based

"""Command-line entry point for rule-based page scoring.

Run from the repository root with:

    python -m graph_datasheet_extractor.preprocessing.main_score_pages_rule_based

Default input:

    outputs/intermediate/page_texts.json

Default output:

    outputs/intermediate/page_scores_rule_based.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from graph_datasheet_extractor.preprocessing.rule_based_page_scorer import (
    RuleBasedPageScoringError,
    load_page_texts_json,
    score_pages_rule_based,
    write_page_scores_json,
)


DEFAULT_INPUT_JSON = Path("outputs/intermediate/page_texts.json")
DEFAULT_OUTPUT_JSON = Path("outputs/intermediate/page_scores_rule_based.json")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Score extracted PDF pages using deterministic rule-based screening."
    )

    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_INPUT_JSON,
        help=f"Path to page_texts.json. Default: {DEFAULT_INPUT_JSON}",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help=f"Path to rule-based page score JSON. Default: {DEFAULT_OUTPUT_JSON}",
    )

    return parser.parse_args()


def main() -> None:
    """Run rule-based page scoring and write the result to JSON."""

    args = parse_args()

    input_json: Path = args.input
    output_json: Path = args.output

    print("=== Rule-based Page Scoring ===")
    print(f"Input JSON : {input_json}")
    print(f"Output JSON: {output_json}")
    print()

    try:
        payload = load_page_texts_json(input_json)
        result = score_pages_rule_based(payload)
        write_page_scores_json(result, output_json)

    except FileNotFoundError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except RuleBasedPageScoringError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except ValueError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    sorted_pages = sorted(result.pages, key=lambda page: page.score, reverse=True)

    print("Result: PASSED")
    print()
    print("Scoring summary:")
    print(f"- Source file : {result.source_file}")
    print(f"- Pages scored: {result.page_count}")
    print()
    print("Pages by score:")

    for page in sorted_pages:
        print(
            f"- Page {page.page_number}: "
            f"score={page.score}, "
            f"level={page.relevance_level}, "
            f"categories={', '.join(page.matched_categories) if page.matched_categories else 'None'}"
        )

    print()
    print(f"Written to: {output_json}")


if __name__ == "__main__":
    main()