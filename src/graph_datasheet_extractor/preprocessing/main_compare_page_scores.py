# $env:PYTHONPATH="src"
# python -m graph_datasheet_extractor.preprocessing.main_compare_page_scores

"""Command-line entry point for running and comparing page scoring methods.

This runner directly executes:

1. rule-based page scoring
2. LLM-based page scoring
3. comparison between both scoring outputs

Run from the repository root with:

    python -m graph_datasheet_extractor.preprocessing.main_compare_page_scores

Default input:

    outputs/intermediate/page_texts.json

Default outputs:

    outputs/intermediate/page_scores_rule_based.json
    outputs/intermediate/page_scores_llm_based.json
    outputs/intermediate/page_score_comparison.json

Environment variables:

    OPENAI_API_KEY=your_openai_api_key_here

Optional:

    LLM_MODEL=gpt-4o-mini
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from graph_datasheet_extractor.preprocessing.llm_page_scorer import (
    LLMPageScoringError,
    score_pages_llm_based,
    write_page_scores_json as write_llm_page_scores_json,
)
from graph_datasheet_extractor.preprocessing.page_score_comparator import (
    PageScoreComparisonError,
    compare_page_scores,
    write_page_score_comparison_json,
)
from graph_datasheet_extractor.preprocessing.rule_based_page_scorer import (
    RuleBasedPageScoringError,
    load_page_texts_json,
    score_pages_rule_based,
    scoring_result_to_dict as rule_based_result_to_dict,
    write_page_scores_json as write_rule_based_page_scores_json,
)
from graph_datasheet_extractor.preprocessing.llm_page_scorer import (
    scoring_result_to_dict as llm_based_result_to_dict,
)


DEFAULT_PAGE_TEXTS_INPUT = Path("outputs/intermediate/page_texts.json")
DEFAULT_RULE_BASED_OUTPUT = Path("outputs/intermediate/page_scores_rule_based.json")
DEFAULT_LLM_BASED_OUTPUT = Path("outputs/intermediate/page_scores_llm_based.json")
DEFAULT_COMPARISON_OUTPUT = Path("outputs/intermediate/page_score_comparison.json")
DEFAULT_MODEL = "gpt-4o-mini"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Run rule-based and LLM-based page scoring, then compare the results."
        )
    )

    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_PAGE_TEXTS_INPUT,
        help=f"Path to page_texts.json. Default: {DEFAULT_PAGE_TEXTS_INPUT}",
    )

    parser.add_argument(
        "--rule-output",
        type=Path,
        default=DEFAULT_RULE_BASED_OUTPUT,
        help=(
            "Path to write rule-based page scores. "
            f"Default: {DEFAULT_RULE_BASED_OUTPUT}"
        ),
    )

    parser.add_argument(
        "--llm-output",
        type=Path,
        default=DEFAULT_LLM_BASED_OUTPUT,
        help=(
            "Path to write LLM-based page scores. "
            f"Default: {DEFAULT_LLM_BASED_OUTPUT}"
        ),
    )

    parser.add_argument(
        "--comparison-output",
        "-o",
        type=Path,
        default=DEFAULT_COMPARISON_OUTPUT,
        help=(
            "Path to write page score comparison JSON. "
            f"Default: {DEFAULT_COMPARISON_OUTPUT}"
        ),
    )

    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help=(
            "LLM model name. If omitted, uses LLM_MODEL from environment, "
            f"or falls back to {DEFAULT_MODEL}."
        ),
    )

    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help=(
            "Only run rule-based scoring. "
            "Comparison is skipped because LLM-based scores are not generated."
        ),
    )

    return parser.parse_args()


def resolve_model_name(cli_model: str | None) -> str:
    """Resolve LLM model name from CLI argument, environment, or default."""

    if cli_model:
        return cli_model

    env_model = os.getenv("LLM_MODEL")
    if env_model:
        return env_model

    return DEFAULT_MODEL


def print_rule_based_summary(result) -> None:
    """Print rule-based scoring summary."""

    sorted_pages = sorted(result.pages, key=lambda page: page.score, reverse=True)

    print()
    print("Rule-based scoring summary:")
    print(f"- Source file : {result.source_file}")
    print(f"- Pages scored: {result.page_count}")
    print("Pages by rule-based score:")

    for page in sorted_pages:
        print(
            f"- Page {page.page_number}: "
            f"score={page.score}, "
            f"level={page.relevance_level}, "
            f"categories={', '.join(page.matched_categories) if page.matched_categories else 'None'}"
        )


def print_llm_based_summary(result) -> None:
    """Print LLM-based scoring summary."""

    sorted_pages = sorted(result.pages, key=lambda page: page.score, reverse=True)

    print()
    print("LLM-based scoring summary:")
    print(f"- Source file : {result.source_file}")
    print(f"- Pages scored: {result.page_count}")
    print(f"- LLM model   : {result.llm_model}")
    print("Pages by LLM-based score:")

    for page in sorted_pages:
        targets = ", ".join(page.extraction_targets_found)
        if not targets:
            targets = "None"

        print(
            f"- Page {page.page_number}: "
            f"score={page.score}, "
            f"level={page.relevance_level}, "
            f"useful={page.useful_for_extraction}, "
            f"type={page.likely_content_type}, "
            f"targets={targets}"
        )


def print_comparison_summary(result) -> None:
    """Print comparison summary."""

    summary = result.summary

    print()
    print("Comparison summary:")
    print(f"- Pages compared               : {summary.page_count}")
    print(f"- Same source file             : {summary.same_source_file}")
    print(f"- Level agreement count        : {summary.agreement_on_level_count}")
    print(f"- Selection agreement count    : {summary.agreement_on_selection_count}")
    print(f"- Level disagreement pages     : {summary.pages_with_level_disagreement}")
    print(f"- Selection disagreement pages : {summary.pages_with_selection_disagreement}")
    print(f"- Rule-based selected pages    : {summary.rule_based_selected_pages}")
    print(f"- LLM-based selected pages     : {summary.llm_based_selected_pages}")
    print(f"- Intersection selected pages  : {summary.intersection_selected_pages}")
    print(f"- Rule-only selected pages     : {summary.rule_only_selected_pages}")
    print(f"- LLM-only selected pages      : {summary.llm_only_selected_pages}")

    print()
    print("Per-page comparison:")

    for page in result.pages:
        print(
            f"- Page {page.page_number}: "
            f"rule={page.rule_based_level}({page.rule_based_score}, rank {page.rule_based_rank}) | "
            f"llm={page.llm_level}({page.llm_score}, rank {page.llm_rank}) | "
            f"selection_agreement={page.agreement_on_selection}"
        )


def main() -> None:
    """Run rule-based and LLM-based page scoring, then compare outputs."""

    load_dotenv()

    args = parse_args()

    input_json: Path = args.input
    rule_output_json: Path = args.rule_output
    llm_output_json: Path = args.llm_output
    comparison_output_json: Path = args.comparison_output
    model_name = resolve_model_name(args.model)

    print("=== Page Scoring and Comparison Runner ===")
    print(f"Input page texts       : {input_json}")
    print(f"Rule-based output      : {rule_output_json}")
    print(f"LLM-based output       : {llm_output_json}")
    print(f"Comparison output      : {comparison_output_json}")
    print(f"LLM model              : {model_name}")
    print(f"Skip LLM               : {args.skip_llm}")
    print()

    try:
        page_texts_payload = load_page_texts_json(input_json)

        print("Running rule-based page scoring...")
        rule_based_result = score_pages_rule_based(page_texts_payload)
        write_rule_based_page_scores_json(rule_based_result, rule_output_json)
        print(f"Rule-based scores written to: {rule_output_json}")
        print_rule_based_summary(rule_based_result)

        if args.skip_llm:
            print()
            print("Result: PASSED")
            print("LLM-based scoring and comparison were skipped.")
            return

        if not os.getenv("OPENAI_API_KEY"):
            print()
            print("Result: FAILED")
            print("Reason: OPENAI_API_KEY is not set.")
            raise SystemExit(1)

        print()
        print("Running LLM-based page scoring...")
        llm_based_result = score_pages_llm_based(
            page_texts_payload=page_texts_payload,
            model_name=model_name,
        )
        write_llm_page_scores_json(llm_based_result, llm_output_json)
        print(f"LLM-based scores written to: {llm_output_json}")
        print_llm_based_summary(llm_based_result)

        print()
        print("Comparing rule-based and LLM-based page scores...")

        rule_based_payload = rule_based_result_to_dict(rule_based_result)
        llm_based_payload = llm_based_result_to_dict(llm_based_result)

        comparison_result = compare_page_scores(
            rule_based_payload=rule_based_payload,
            llm_based_payload=llm_based_payload,
        )

        write_page_score_comparison_json(
            comparison_result,
            comparison_output_json,
        )

        print(f"Comparison written to: {comparison_output_json}")
        print_comparison_summary(comparison_result)

    except FileNotFoundError as exc:
        print()
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except RuleBasedPageScoringError as exc:
        print()
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except LLMPageScoringError as exc:
        print()
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except PageScoreComparisonError as exc:
        print()
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except ValueError as exc:
        print()
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    print()
    print("Result: PASSED")


if __name__ == "__main__":
    main()