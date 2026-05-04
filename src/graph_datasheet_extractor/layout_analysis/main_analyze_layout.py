# .\.venv\Scripts\Activate.ps1
# $env:PYTHONPATH="src"
# python -m graph_datasheet_extractor.layout_analysis.main_analyze_layout

# python -m graph_datasheet_extractor.layout_analysis.main_analyze_layout --backend pypdf
# python -m graph_datasheet_extractor.layout_analysis.main_analyze_layout --backend docling
# python -m graph_datasheet_extractor.layout_analysis.main_analyze_layout --backend dolphin

"""Command-line entry point for layout analysis.

Run from the repository root with:

    python -m graph_datasheet_extractor.layout_analysis.main_analyze_layout

Supported backends:

    pypdf
    docling
    dolphin

Examples:

    python -m graph_datasheet_extractor.layout_analysis.main_analyze_layout --backend pypdf

    python -m graph_datasheet_extractor.layout_analysis.main_analyze_layout --backend docling

    python -m graph_datasheet_extractor.layout_analysis.main_analyze_layout --backend dolphin

Default inputs:

    pypdf backend:
        outputs/intermediate/page_texts.json

    docling backend:
        data/raw/vishay_temt6000x01_datasheet.pdf

    dolphin backend:
        data/raw/vishay_temt6000x01_datasheet.pdf

Default outputs:

    pypdf backend:
        outputs/intermediate/layout_blocks_pypdf.json

    docling backend:
        outputs/intermediate/layout_blocks_docling.json

    dolphin backend:
        outputs/intermediate/layout_blocks_dolphin.json

For Dolphin:

    If outputs/intermediate/dolphin_raw_output.json exists, it is used directly.

    Otherwise, set DOLPHIN_COMMAND in .env. The command may contain:
        {input_pdf}
        {raw_output}

Example:
    DOLPHIN_COMMAND=python C:/Tools/Dolphin/demo_page.py --input {input_pdf} --output {raw_output}
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from graph_datasheet_extractor.layout_analysis.layout_models import (
    LayoutAnalysisResult,
)
from graph_datasheet_extractor.layout_analysis.pypdf_layout_analyzer import (
    LAYOUT_BACKEND as PYPDF_LAYOUT_BACKEND,
    PypdfLayoutAnalysisError,
    analyze_layout_from_page_texts,
    load_page_texts_json,
    write_layout_blocks_json as write_pypdf_layout_blocks_json,
)


DEFAULT_PYPDF_INPUT_JSON = Path("outputs/intermediate/page_texts.json")
DEFAULT_PDF_INPUT = Path("data/raw/vishay_temt6000x01_datasheet.pdf")

DEFAULT_PYPDF_OUTPUT_JSON = Path("outputs/intermediate/layout_blocks_pypdf.json")
DEFAULT_DOCLING_OUTPUT_JSON = Path("outputs/intermediate/layout_blocks_docling.json")
DEFAULT_DOLPHIN_OUTPUT_JSON = Path("outputs/intermediate/layout_blocks_dolphin.json")

DEFAULT_DOLPHIN_RAW_OUTPUT_JSON = Path("outputs/intermediate/dolphin_raw_output.json")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Analyze layout blocks from a datasheet document."
    )

    parser.add_argument(
        "--backend",
        "-b",
        type=str,
        choices=["pypdf", "docling", "dolphin"],
        default="pypdf",
        help="Layout analysis backend. Default: pypdf",
    )

    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=None,
        help=(
            "Input path. For pypdf backend, this should be page_texts.json. "
            "For docling/dolphin backend, this should be a PDF file."
        ),
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Path to output layout_blocks JSON.",
    )

    parser.add_argument(
        "--dolphin-raw-output",
        type=Path,
        default=None,
        help=(
            "Path to Dolphin raw JSON output. If it exists, it is read directly. "
            "If it does not exist, DOLPHIN_COMMAND is used when available."
        ),
    )

    parser.add_argument(
        "--no-run-dolphin",
        action="store_true",
        help=(
            "For Dolphin backend only: do not run external DOLPHIN_COMMAND "
            "when the raw output file is missing."
        ),
    )

    return parser.parse_args()


def resolve_input_path(backend: str, cli_input: Path | None) -> Path:
    """Resolve input path based on backend and optional CLI argument."""

    if cli_input is not None:
        return cli_input

    if backend == "pypdf":
        return DEFAULT_PYPDF_INPUT_JSON

    if backend in {"docling", "dolphin"}:
        return DEFAULT_PDF_INPUT

    raise ValueError(f"Unsupported backend: {backend}")


def resolve_output_path(backend: str, cli_output: Path | None) -> Path:
    """Resolve output path based on backend and optional CLI argument."""

    if cli_output is not None:
        return cli_output

    if backend == "pypdf":
        return DEFAULT_PYPDF_OUTPUT_JSON

    if backend == "docling":
        return DEFAULT_DOCLING_OUTPUT_JSON

    if backend == "dolphin":
        return DEFAULT_DOLPHIN_OUTPUT_JSON

    raise ValueError(f"Unsupported backend: {backend}")


def resolve_dolphin_raw_output_path(cli_raw_output: Path | None) -> Path:
    """Resolve Dolphin raw output path."""

    if cli_raw_output is not None:
        return cli_raw_output

    return DEFAULT_DOLPHIN_RAW_OUTPUT_JSON


def run_pypdf_backend(input_path: Path, output_path: Path) -> LayoutAnalysisResult:
    """Run lightweight pypdf baseline backend."""

    page_texts_payload = load_page_texts_json(input_path)
    result = analyze_layout_from_page_texts(page_texts_payload)
    write_pypdf_layout_blocks_json(result, output_path)

    return result


def run_docling_backend(input_path: Path, output_path: Path) -> LayoutAnalysisResult:
    """Run Docling layout backend."""

    try:
        from graph_datasheet_extractor.layout_analysis.docling_layout_analyzer import (
            DoclingLayoutAnalysisError,
            analyze_layout_with_docling,
            write_layout_blocks_json as write_docling_layout_blocks_json,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Could not import docling_layout_analyzer.py. "
            "Please check that the file exists under "
            "src/graph_datasheet_extractor/layout_analysis/."
        ) from exc

    try:
        result = analyze_layout_with_docling(input_path)
        write_docling_layout_blocks_json(result, output_path)
        return result

    except DoclingLayoutAnalysisError:
        raise


def run_dolphin_backend(
    input_path: Path,
    output_path: Path,
    raw_output_path: Path,
    run_if_missing: bool,
) -> LayoutAnalysisResult:
    """Run Dolphin layout backend."""

    try:
        from graph_datasheet_extractor.layout_analysis.dolphin_layout_analyzer import (
            DolphinLayoutAnalysisError,
            analyze_layout_with_dolphin,
            write_layout_blocks_json as write_dolphin_layout_blocks_json,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Could not import dolphin_layout_analyzer.py. "
            "Please check that the file exists under "
            "src/graph_datasheet_extractor/layout_analysis/."
        ) from exc

    try:
        result = analyze_layout_with_dolphin(
            pdf_path=input_path,
            raw_output_path=raw_output_path,
            run_if_missing=run_if_missing,
        )
        write_dolphin_layout_blocks_json(result, output_path)
        return result

    except DolphinLayoutAnalysisError:
        raise


def print_layout_summary(result: LayoutAnalysisResult, output_path: Path) -> None:
    """Print layout analysis summary."""

    block_type_counter = Counter(block.block_type for block in result.blocks)
    page_block_counter = Counter(block.page_number for block in result.blocks)

    print("Result: PASSED")
    print()
    print("Layout analysis summary:")
    print(f"- Source file : {result.source_file}")
    print(f"- Backend     : {result.layout_backend}")
    print(f"- Pages       : {result.page_count}")
    print(f"- Blocks      : {len(result.blocks)}")
    print()
    print("Blocks by type:")

    for block_type, count in sorted(block_type_counter.items()):
        print(f"- {block_type}: {count}")

    print()
    print("Blocks by page:")

    for page_number, count in sorted(page_block_counter.items()):
        print(f"- Page {page_number}: {count} block(s)")

    print()
    print(f"Written to: {output_path}")


def main() -> None:
    """Run selected layout analysis backend and write layout blocks JSON."""

    args = parse_args()

    backend: str = args.backend
    input_path = resolve_input_path(backend, args.input)
    output_path = resolve_output_path(backend, args.output)
    dolphin_raw_output_path = resolve_dolphin_raw_output_path(args.dolphin_raw_output)

    print("=== Layout Analysis ===")
    print(f"Backend    : {backend}")
    print(f"Input path : {input_path}")
    print(f"Output JSON: {output_path}")

    if backend == "pypdf":
        print(f"Backend id : {PYPDF_LAYOUT_BACKEND}")

    if backend == "dolphin":
        print(f"Dolphin raw output: {dolphin_raw_output_path}")
        print(f"Run Dolphin if missing: {not args.no_run_dolphin}")

    print()

    try:
        if backend == "pypdf":
            result = run_pypdf_backend(input_path, output_path)

        elif backend == "docling":
            result = run_docling_backend(input_path, output_path)

        elif backend == "dolphin":
            result = run_dolphin_backend(
                input_path=input_path,
                output_path=output_path,
                raw_output_path=dolphin_raw_output_path,
                run_if_missing=not args.no_run_dolphin,
            )

        else:
            raise ValueError(f"Unsupported backend: {backend}")

        print_layout_summary(result, output_path)

    except FileNotFoundError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except PypdfLayoutAnalysisError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except RuntimeError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc

    except ValueError as exc:
        print("Result: FAILED")
        print(f"Reason: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()