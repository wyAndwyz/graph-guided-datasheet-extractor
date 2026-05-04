# $env:PYTHONPATH="src"
# python -m graph_datasheet_extractor.preprocessing.main_score_pages_llm_based

"""Command-line entry point for LLM-based page scoring.

Run from the repository root with:

    python -m graph_datasheet_extractor.preprocessing.main_score_pages_llm_based

Default input:

    outputs/intermediate/page_texts.json

Default output:

    outputs/intermediate/page_scores_llm_based.json

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
    load_page_texts_json,
    score_pages_llm_based,
    write_page_scores_json,
)


DEFAULT_INPUT_JSON = Path("outputs/intermediate/page_texts.json")
DEFAULT_OUTPUT_JSON = Path("outputs/intermediate/page_scores_llm_based.json")
DEFAULT_MODEL = "gpt-4o-mini"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Score extracted PDF pages using LLM-assisted document screening."
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
        help=f"Path to LLM-based page score JSON. Default: {DEFAULT_OUTPUT_JSON}",
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

    return parser.parse_args()


def resolve_model_name(cli_model: str | None) -> str:
    """Resolve LLM model name from CLI argument, environment, or default."""

    if cli_model:
        return cli_model

    env_model = os.getenv("LLM_MODEL")
    if env_model:
        return env_model

    return DEFAULT_MODEL


def main() -> None:
    """Run LLM-based page scoring and write the result to JSON."""

    load_dotenv()

    args = parse_args()

    input_json: Path = args.input
    output_json: Path = args.output
    model_name = resolve_model_name(args.model)

    print("=== LLM-based Page Scoring ===")
    print(f"Input JSON : {input_json}")
    print(f"Output JSON: {output_json}")
    print(f"LLM model  : {model_name}")
    print()

    if not os.getenv("OPENAI_API_KEY"):
        print("Result: FAILED")
        print("Reason: OPENAI_API_KEY is not set.")
        raise SystemExit(1)

    try:
        payload = load_page_texts_json(input_json)
        result = score_pages_llm_based(
            page_texts_payload=payload,
            model_name=model_name,
        )
        write_page_scores_json(result, output_json)

    except FileNotFoundError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except LLMPageScoringError as exc:
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
    print(f"- LLM model   : {result.llm_model}")
    print()
    print("Pages by score:")

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

    print()
    print(f"Written to: {output_json}")


if __name__ == "__main__":
    main()