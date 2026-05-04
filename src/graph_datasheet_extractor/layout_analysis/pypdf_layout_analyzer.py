"""Lightweight pypdf-based layout analyzer.

This module implements the first baseline layout analyzer.

Input:
    outputs/intermediate/page_texts.json

Output:
    outputs/intermediate/layout_blocks.json

Important:
This is not a real visual layout model. It uses the already extracted page text
and simple heuristics to create coarse layout blocks.

The goal is to establish a stable layout_blocks.json schema so that later
backends such as Docling, Dolphin, MinerU, or OCR/layout models can be added
without changing downstream pipeline steps.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from graph_datasheet_extractor.layout_analysis.layout_models import (
    LayoutAnalysisResult,
    LayoutBlock,
    LayoutBlockType,
    layout_analysis_result_to_dict,
    make_block_id,
)


class PypdfLayoutAnalysisError(RuntimeError):
    """Raised when pypdf baseline layout analysis fails."""


LAYOUT_BACKEND = "pypdf_baseline"


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

FIGURE_CUE_PATTERNS = [
    r"\bFig\.\s*\d+",
    r"\bFigure\s+\d+",
]


def load_page_texts_json(input_path: str | Path) -> dict[str, Any]:
    """Load page-level text extraction JSON."""

    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Page texts JSON not found: {input_path}")

    try:
        return json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PypdfLayoutAnalysisError(f"Invalid JSON file: {input_path}") from exc


def _normalize_line(line: str) -> str:
    """Normalize one line while keeping its local text content."""

    return line.strip()


def _clean_lines(text: str) -> list[str]:
    """Split page text into non-empty normalized lines."""

    return [
        _normalize_line(line)
        for line in text.splitlines()
        if _normalize_line(line)
    ]


def _is_known_heading(line: str) -> bool:
    """Return whether a line is a known section heading."""

    line_stripped = line.strip()
    line_upper = line_stripped.upper()

    for heading in KNOWN_SECTION_HEADINGS:
        if line_upper == heading.upper():
            return True

    return False


def _detect_heading_in_line(line: str) -> str | None:
    """Detect a known heading that appears inside a line.

    Some pypdf outputs can merge a heading with the following table content.
    This helper detects the heading even if the line is not only the heading.
    """

    line_upper = line.upper()

    # Prefer longer headings first to avoid partial matches.
    for heading in sorted(KNOWN_SECTION_HEADINGS, key=len, reverse=True):
        heading_upper = heading.upper()
        if heading_upper in line_upper:
            return heading

    return None


def _contains_any(text: str, terms: list[str]) -> bool:
    """Case-insensitive containment check for a list of terms."""

    text_lower = text.lower()
    return any(term.lower() in text_lower for term in terms)


def _matches_any_regex(text: str, patterns: list[str]) -> bool:
    """Regex pattern check."""

    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _looks_table_like(text: str) -> bool:
    """Heuristic detection for table-like blocks."""

    upper_text = text.upper()

    cue_count = sum(1 for cue in TABLE_CUE_TERMS if cue.upper() in upper_text)

    # Strong signal: contains several table header cues.
    if cue_count >= 3:
        return True

    # Common datasheet row-like pattern: symbol/value/unit-like content.
    if re.search(r"\b(VCEO|VECO|IPCE|TAMB|TSTG|PV|IC|TSD)\b", upper_text):
        if re.search(r"\b(V|MA|MW|PF|NM|DEG|°C|K/W|μA|µA)\b", text, flags=re.IGNORECASE):
            return True

    return False


def _classify_block_type(text: str, section_heading: str | None) -> LayoutBlockType:
    """Assign a coarse layout block type using simple heuristics."""

    stripped = text.strip()

    if not stripped:
        return "unknown"

    if _is_known_heading(stripped):
        return "heading"

    if _contains_any(stripped, LEGAL_CUE_TERMS):
        # A single technical page may contain a short disclaimer line in the header.
        # If the block is short and not the legal page itself, classify it as boilerplate.
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

    if stripped.startswith("•"):
        return "list"

    if len(stripped) < 80 and stripped.isupper():
        return "heading"

    return "paragraph"


def _split_page_into_blocks(page_number: int, page_text: str) -> list[LayoutBlock]:
    """Split one page text into coarse layout blocks.

    The baseline heuristic is heading-aware:
    - starts a new block at known section headings;
    - keeps lines under the current section together;
    - creates separate figure blocks for figure-heavy lines.
    """

    lines = _clean_lines(page_text)

    if not lines:
        return [
            LayoutBlock(
                block_id=make_block_id(page_number, 1),
                page_number=page_number,
                block_index=1,
                block_type="unknown",
                text="",
                char_count=0,
                reading_order=1,
                section_heading=None,
                bbox=None,
                metadata={
                    "source": LAYOUT_BACKEND,
                    "heuristic": "empty_page",
                    "confidence": None,
                },
            )
        ]

    raw_blocks: list[dict[str, Any]] = []
    current_lines: list[str] = []
    current_heading: str | None = None

    def flush_current_block() -> None:
        nonlocal current_lines, current_heading

        if not current_lines:
            return

        block_text = "\n".join(current_lines).strip()

        if block_text:
            raw_blocks.append(
                {
                    "text": block_text,
                    "section_heading": current_heading,
                }
            )

        current_lines = []

    for line in lines:
        is_heading = _is_known_heading(line)

        # Figure-heavy lines can be useful as separate blocks.
        is_figure_line = _matches_any_regex(line, FIGURE_CUE_PATTERNS)

        if is_heading:
            flush_current_block()
            current_heading = line.strip()
            current_lines = [line.strip()]
            flush_current_block()
            continue

        detected_heading = _detect_heading_in_line(line)

        if detected_heading and detected_heading.upper() != (current_heading or "").upper():
            flush_current_block()
            current_heading = detected_heading

        if is_figure_line and current_lines:
            flush_current_block()
            current_lines = [line]
            flush_current_block()
            continue

        current_lines.append(line)

    flush_current_block()

    blocks: list[LayoutBlock] = []

    for block_index, raw_block in enumerate(raw_blocks, start=1):
        block_text = str(raw_block["text"]).strip()
        section_heading = raw_block.get("section_heading")
        block_type = _classify_block_type(block_text, section_heading)

        blocks.append(
            LayoutBlock(
                block_id=make_block_id(page_number, block_index),
                page_number=page_number,
                block_index=block_index,
                block_type=block_type,
                text=block_text,
                char_count=len(block_text),
                reading_order=block_index,
                section_heading=section_heading,
                bbox=None,
                metadata={
                    "source": LAYOUT_BACKEND,
                    "heuristic": "heading_and_line_based_split",
                    "confidence": None,
                },
            )
        )

    return blocks


def analyze_layout_from_page_texts(
    page_texts_payload: dict[str, Any],
) -> LayoutAnalysisResult:
    """Analyze layout from page-level text extraction payload."""

    source_file = str(page_texts_payload.get("source_file", ""))
    pages_payload = page_texts_payload.get("pages", [])

    if not isinstance(pages_payload, list):
        raise PypdfLayoutAnalysisError("Expected 'pages' to be a list.")

    all_blocks: list[LayoutBlock] = []

    for page in pages_payload:
        if "page_number" not in page:
            raise PypdfLayoutAnalysisError(f"Missing page_number in page entry: {page}")

        page_number = int(page["page_number"])
        page_text = str(page.get("text", ""))

        page_blocks = _split_page_into_blocks(
            page_number=page_number,
            page_text=page_text,
        )
        all_blocks.extend(page_blocks)

    return LayoutAnalysisResult(
        source_file=source_file,
        layout_backend=LAYOUT_BACKEND,
        page_count=len(pages_payload),
        blocks=all_blocks,
    )


def write_layout_blocks_json(
    result: LayoutAnalysisResult,
    output_path: str | Path,
) -> Path:
    """Write layout analysis result to JSON."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(layout_analysis_result_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def analyze_layout_file_with_pypdf_baseline(
    input_path: str | Path,
    output_path: str | Path,
) -> Path:
    """Convenience function: load page_texts.json, analyze layout, and write JSON."""

    payload = load_page_texts_json(input_path)
    result = analyze_layout_from_page_texts(payload)
    return write_layout_blocks_json(result, output_path)