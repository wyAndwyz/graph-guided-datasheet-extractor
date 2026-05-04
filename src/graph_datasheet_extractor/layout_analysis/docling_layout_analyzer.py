# $env:PYTHONPATH="src"
# python -m graph_datasheet_extractor.layout_analysis.main_analyze_layout `
#   --backend dolphin `
#   --dolphin-raw-output outputs/intermediate/dolphin_raw_output.json `
#   --no-run-dolphin


"""Docling-based layout analyzer.

This module implements an optional Docling backend for layout analysis.

Input:
    data/raw/vishay_temt6000x01_datasheet.pdf

Output:
    outputs/intermediate/layout_blocks_docling.json

Important:
Docling is treated as an optional dependency. If it is not installed, this
module raises a clear error message instead of failing with an unclear import
error.

If Docling downloads models from Hugging Face, the local .env variable

    HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx

can be used to authenticate Hugging Face Hub requests. The token is optional
for public models, but recommended for more stable downloads and higher rate
limits.

This adapter is intentionally defensive:
- it loads HF_TOKEN from the local .env file before initializing Docling;
- it checks the input PDF;
- it checks whether Docling is installed;
- it catches conversion errors;
- it avoids relying on unstable internal Docling object fields;
- it primarily uses the public export_to_markdown() method;
- it maps the result into the shared LayoutAnalysisResult schema.

The output is not expected to be perfect visual layout. It is a practical
document-structure representation that can later be replaced or enriched by
a stronger backend such as Dolphin.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from graph_datasheet_extractor.layout_analysis.layout_models import (
    LayoutAnalysisResult,
    LayoutBlock,
    LayoutBlockType,
    layout_analysis_result_to_dict,
    make_block_id,
)


class DoclingLayoutAnalysisError(RuntimeError):
    """Raised when Docling-based layout analysis fails."""


LAYOUT_BACKEND = "docling_markdown"


KNOWN_SECTION_HEADINGS = [
    "DESCRIPTION",
    "FEATURES",
    "APPLICATIONS",
    "PRODUCT SUMMARY",
    "ORDERING INFORMATION",
    "ABSOLUTE MAXIMUM RATINGS",
    "BASIC CHARACTERISTICS",
    "REFLOW SOLDER PROFILE",
    "DRYPACK",
    "FLOOR LIFE",
    "DRYING",
    "PACKAGE DIMENSIONS",
    "BLISTER TAPE DIMENSIONS",
    "REEL DIMENSIONS",
    "Legal Disclaimer Notice",
    "Disclaimer",
]

TABLE_CUE_TERMS = [
    "PARAMETER",
    "TEST CONDITION",
    "SYMBOL",
    "VALUE",
    "UNIT",
    "MIN.",
    "TYP.",
    "MAX.",
]

LEGAL_CUE_TERMS = [
    "Legal Disclaimer",
    "Disclaimer",
    "ALL RIGHTS RESERVED",
    "liability",
    "warranty",
    "No license",
    "third-party websites",
]

PACKAGE_ONLY_CUE_TERMS = [
    "BLISTER TAPE DIMENSIONS",
    "REEL DIMENSIONS",
    "Volume:",
    "pcs/reel",
]

TABLE_CUE_PATTERNS = [
    r"\btab\.\s*\d+",
    r"\btable\s*\d+",
    r"\btab\s*\d+",
    r"\btabelle\s*\d+",
]

FIGURE_CUE_PATTERNS = [
    r"\bFig\.\s*\d+",
    r"\bFigure\s+\d+",
]


def _configure_huggingface_token_from_env() -> None:
    """Load HF_TOKEN from .env and expose it to Hugging Face libraries.

    The project uses the standard variable name HF_TOKEN.

    huggingface_hub and related libraries may also check
    HUGGINGFACE_HUB_TOKEN. If HF_TOKEN exists and HUGGINGFACE_HUB_TOKEN is not
    already set, this function maps HF_TOKEN to HUGGINGFACE_HUB_TOKEN.

    The token is never printed or logged.
    """

    load_dotenv()

    hf_token = os.getenv("HF_TOKEN")

    if not hf_token:
        return

    if not os.getenv("HUGGINGFACE_HUB_TOKEN"):
        os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token


def _validate_pdf_path(pdf_path: str | Path) -> Path:
    """Validate local PDF path."""

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if not pdf_path.is_file():
        raise ValueError(f"Expected a file path, got: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {pdf_path}")

    return pdf_path


def _get_docling_converter():
    """Create a Docling DocumentConverter instance."""

    _configure_huggingface_token_from_env()

    try:
        from docling.document_converter import DocumentConverter
    except ImportError as exc:
        raise DoclingLayoutAnalysisError(
            "Missing optional dependency 'docling'. "
            "Install it with: pip install docling"
        ) from exc

    try:
        return DocumentConverter()
    except Exception as exc:  # pragma: no cover - external dependency
        raise DoclingLayoutAnalysisError(
            "Failed to initialize Docling DocumentConverter."
        ) from exc


def _convert_pdf_to_docling_document(pdf_path: Path):
    """Convert PDF to a Docling document."""

    converter = _get_docling_converter()

    try:
        conversion_result = converter.convert(str(pdf_path))
    except Exception as exc:  # pragma: no cover - external dependency
        raise DoclingLayoutAnalysisError(
            f"Docling failed to convert PDF: {pdf_path}"
        ) from exc

    document = getattr(conversion_result, "document", None)

    if document is None:
        raise DoclingLayoutAnalysisError(
            "Docling conversion result does not contain a document object."
        )

    return document


def _export_document_to_markdown(document: Any) -> str:
    """Export a Docling document to Markdown using the public API if available."""

    export_to_markdown = getattr(document, "export_to_markdown", None)

    if not callable(export_to_markdown):
        raise DoclingLayoutAnalysisError(
            "Docling document does not provide export_to_markdown()."
        )

    try:
        markdown = export_to_markdown()
    except Exception as exc:  # pragma: no cover - external dependency
        raise DoclingLayoutAnalysisError(
            "Docling failed to export document to Markdown."
        ) from exc

    if not isinstance(markdown, str):
        raise DoclingLayoutAnalysisError(
            "Docling export_to_markdown() did not return a string."
        )

    if not markdown.strip():
        raise DoclingLayoutAnalysisError(
            "Docling exported empty Markdown content."
        )

    return markdown


def _contains_any(text: str, terms: list[str]) -> bool:
    """Case-insensitive containment check."""

    text_lower = text.lower()
    return any(term.lower() in text_lower for term in terms)


def _matches_any_regex(text: str, patterns: list[str]) -> bool:
    """Regex pattern check."""

    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _normalize_markdown_line(line: str) -> str:
    """Normalize one Markdown line while preserving useful content."""

    return line.strip()


def _split_markdown_into_paragraph_blocks(markdown: str) -> list[str]:
    """Split Markdown into coarse blocks.

    The logic is intentionally simple:
    - Markdown headings become their own blocks;
    - Markdown tables are kept together;
    - paragraphs are separated by blank lines;
    - list runs are kept together.

    This is more stable than trying to rely on private Docling internals.
    """

    lines = markdown.splitlines()
    blocks: list[str] = []
    current_lines: list[str] = []
    in_table = False
    in_list = False

    def flush_current() -> None:
        nonlocal current_lines, in_table, in_list

        if current_lines:
            block = "\n".join(current_lines).strip()
            if block:
                blocks.append(block)

        current_lines = []
        in_table = False
        in_list = False

    for raw_line in lines:
        line = _normalize_markdown_line(raw_line)

        if not line:
            flush_current()
            continue

        is_heading = line.startswith("#")
        is_table_line = line.startswith("|") and line.endswith("|")
        is_list_line = line.startswith("- ") or line.startswith("* ") or line.startswith("•")

        if is_heading:
            flush_current()
            blocks.append(line)
            continue

        if is_table_line:
            if not in_table:
                flush_current()
                in_table = True
            current_lines.append(line)
            continue

        if is_list_line:
            if not in_list:
                flush_current()
                in_list = True
            current_lines.append(line)
            continue

        if in_table or in_list:
            flush_current()

        current_lines.append(line)

    flush_current()

    return blocks


def _infer_page_number_from_block_text(block_text: str, current_page: int) -> int:
    """Infer page number from Docling Markdown when possible.

    Some exported Markdown does not explicitly preserve page boundaries. This
    function detects common header patterns in this specific datasheet, but
    falls back to the current page if no reliable signal is found.
    """

    match = re.search(r"Rev\.\s*[\d.]+,\s*[\w-]+\s+(\d+)\s+Document Number", block_text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return current_page

    match = re.search(r"Document Number:\s*\d+\s*\n?", block_text)
    if "Legal Disclaimer" in block_text:
        # The legal disclaimer is appended after the technical datasheet pages.
        # If no better page marker is available, keep it on the current page.
        return current_page

    return current_page


def _detect_section_heading(block_text: str) -> str | None:
    """Detect section heading from a Markdown block."""

    stripped = block_text.strip()
    stripped_no_hash = stripped.lstrip("#").strip()
    upper_text = stripped_no_hash.upper()

    for heading in sorted(KNOWN_SECTION_HEADINGS, key=len, reverse=True):
        if upper_text == heading.upper():
            return heading

    for heading in sorted(KNOWN_SECTION_HEADINGS, key=len, reverse=True):
        if heading.upper() in upper_text:
            return heading

    return None


def _looks_table_like(block_text: str) -> bool:
    """Detect Markdown table or table-like technical content."""

    stripped = block_text.strip()
    upper_text = stripped.upper()

    # Markdown table signal.
    if "|" in stripped and "---" in stripped:
        return True

    # Explicit table captions, e.g. "Table 1", "Tab. 2", "Tabelle 3".
    if _matches_any_regex(stripped, TABLE_CUE_PATTERNS):
        return True

    # Datasheet table header cues.
    table_cue_count = sum(1 for cue in TABLE_CUE_TERMS if cue.upper() in upper_text)

    if table_cue_count >= 3:
        return True

    # Common datasheet row-like pattern: symbol/value/unit-like content.
    if re.search(r"\b(VCEO|VECO|IPCE|TAMB|TSTG|PV|IC|TSD)\b", upper_text):
        if re.search(
            r"\b(V|MA|MW|PF|NM|DEG|°C|K/W|μA|µA)\b",
            stripped,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def _classify_block_type(
    block_text: str,
    section_heading: str | None,
) -> LayoutBlockType:
    """Assign a coarse block type to a Docling Markdown block."""

    stripped = block_text.strip()

    if not stripped:
        return "unknown"

    if stripped.startswith("#"):
        return "heading"

    if _contains_any(stripped, LEGAL_CUE_TERMS):
        if len(stripped) < 300 and "Legal Disclaimer" not in stripped:
            return "boilerplate"
        return "legal"

    if _contains_any(stripped, PACKAGE_ONLY_CUE_TERMS):
        return "package_drawing"

    if section_heading and section_heading.upper() in {
        "PACKAGE DIMENSIONS",
        "BLISTER TAPE DIMENSIONS",
        "REEL DIMENSIONS",
    }:
        return "package_drawing"

    if _matches_any_regex(stripped, FIGURE_CUE_PATTERNS):
        return "figure_or_graph"

    if _looks_table_like(stripped):
        return "table_like"

    if stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("•"):
        return "list"

    if len(stripped) < 100 and stripped.lstrip("#").strip().isupper():
        return "heading"

    return "paragraph"


def _convert_markdown_to_layout_blocks(
    markdown: str,
    source_file: str,
) -> list[LayoutBlock]:
    """Convert Docling Markdown export to shared LayoutBlock objects."""

    raw_blocks = _split_markdown_into_paragraph_blocks(markdown)

    blocks: list[LayoutBlock] = []
    current_page = 1
    page_local_indices: dict[int, int] = {}
    current_section_heading: str | None = None

    for raw_index, block_text in enumerate(raw_blocks, start=1):
        inferred_page = _infer_page_number_from_block_text(block_text, current_page)

        if inferred_page < current_page:
            page_number = current_page
        else:
            page_number = inferred_page
            current_page = inferred_page

        section_heading_candidate = _detect_section_heading(block_text)

        if section_heading_candidate:
            current_section_heading = section_heading_candidate

        page_local_indices[page_number] = page_local_indices.get(page_number, 0) + 1
        block_index = page_local_indices[page_number]

        block_type = _classify_block_type(
            block_text=block_text,
            section_heading=current_section_heading,
        )

        blocks.append(
            LayoutBlock(
                block_id=make_block_id(page_number, block_index),
                page_number=page_number,
                block_index=block_index,
                block_type=block_type,
                text=block_text,
                char_count=len(block_text),
                reading_order=raw_index,
                section_heading=current_section_heading,
                bbox=None,
                metadata={
                    "source": LAYOUT_BACKEND,
                    "source_file": source_file,
                    "raw_markdown_block_index": raw_index,
                    "confidence": None,
                },
            )
        )

    return blocks


def analyze_layout_with_docling(pdf_path: str | Path) -> LayoutAnalysisResult:
    """Analyze PDF layout using Docling and map it to LayoutAnalysisResult."""

    _configure_huggingface_token_from_env()

    pdf_path = _validate_pdf_path(pdf_path)
    document = _convert_pdf_to_docling_document(pdf_path)
    markdown = _export_document_to_markdown(document)

    blocks = _convert_markdown_to_layout_blocks(
        markdown=markdown,
        source_file=str(pdf_path),
    )

    if not blocks:
        raise DoclingLayoutAnalysisError(
            f"Docling produced no layout blocks for PDF: {pdf_path}"
        )

    page_count = max(block.page_number for block in blocks)

    return LayoutAnalysisResult(
        source_file=str(pdf_path),
        layout_backend=LAYOUT_BACKEND,
        page_count=page_count,
        blocks=blocks,
    )


def write_layout_blocks_json(
    result: LayoutAnalysisResult,
    output_path: str | Path,
) -> Path:
    """Write Docling layout analysis result to JSON."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(layout_analysis_result_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def analyze_layout_file_with_docling(
    pdf_path: str | Path,
    output_path: str | Path,
) -> Path:
    """Convenience function: analyze PDF with Docling and write layout JSON."""

    result = analyze_layout_with_docling(pdf_path)
    return write_layout_blocks_json(result, output_path)