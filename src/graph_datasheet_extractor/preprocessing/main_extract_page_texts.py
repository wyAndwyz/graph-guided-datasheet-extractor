# $env:PYTHONPATH="src"
# python -m graph_datasheet_extractor.preprocessing.main_score_pages_rule_based

"""Command-line entry point for extracting page-level text from a PDF datasheet.

Run from the repository root with:

    python -m graph_datasheet_extractor.preprocessing.main_extract_page_texts

Default input:

    data/raw/vishay_temt6000x01_datasheet.pdf

Default output:

    outputs/intermediate/page_texts.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from graph_datasheet_extractor.preprocessing.pdf_text_extractor import (
    PDFTextExtractionError,
    extract_page_texts,
    write_page_texts_json,
)


DEFAULT_INPUT_PDF = Path("data/raw/vishay_temt6000x01_datasheet.pdf")
DEFAULT_OUTPUT_JSON = Path("outputs/intermediate/page_texts.json")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Extract page-level text from a local PDF datasheet."
    )

    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_INPUT_PDF,
        help=f"Path to the input PDF file. Default: {DEFAULT_INPUT_PDF}",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help=f"Path to the output JSON file. Default: {DEFAULT_OUTPUT_JSON}",
    )

    return parser.parse_args()


def main() -> None:
    """Extract page-level text from a PDF and write it to JSON."""

    args = parse_args()

    input_pdf: Path = args.input
    output_json: Path = args.output

    print("=== PDF Page Text Extraction ===")
    print(f"Input PDF  : {input_pdf}")
    print(f"Output JSON: {output_json}")
    print()

    try:
        result = extract_page_texts(input_pdf)
        write_page_texts_json(result, output_json)

    except FileNotFoundError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except ValueError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except PDFTextExtractionError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    total_chars = sum(page.char_count for page in result.pages)
    empty_pages = [page.page_number for page in result.pages if page.char_count == 0]

    print("Result: PASSED")
    print()
    print("Extraction summary:")
    print(f"- Pages extracted : {result.page_count}")
    print(f"- Total characters: {total_chars}")
    print(f"- Empty pages     : {empty_pages if empty_pages else 'None'}")
    print()
    print(f"Written to: {output_json}")


if __name__ == "__main__":
    main()