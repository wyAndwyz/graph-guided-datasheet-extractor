# .\.venv\Scripts\Activate.ps1
# python -m graph_datasheet_extractor.layout_analysis.main_analyze_layout `
#   --backend dolphin `
#   --dolphin-raw-output outputs/intermediate/dolphin_raw_output.json `
#   --no-run-dolphin

"""Dolphin-based layout analyzer adapter.

This module implements a defensive adapter for Dolphin-style document parsing.

Input:
    data/raw/vishay_temt6000x01_datasheet.pdf

Output:
    outputs/intermediate/layout_blocks_dolphin.json

Important:
Dolphin is not treated as a simple built-in Python dependency here. It is a
model/repository-based backend whose local setup may vary.

This adapter therefore supports two modes:

1. Existing raw output mode
   If a Dolphin raw JSON output already exists, this module reads it and maps
   it into the shared LayoutAnalysisResult schema.

2. External command mode
   If DOLPHIN_COMMAND is set in .env, this module runs that command first.
   The command may contain placeholders:
       {input_pdf}
       {raw_output}

Example .env:

    HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
    DOLPHIN_COMMAND=python C:/Tools/Dolphin/demo_page.py --input {input_pdf} --output {raw_output}

Because Dolphin repositories and scripts can change, this adapter avoids
hard-coding one internal Dolphin API. The downstream pipeline only depends on
the shared layout_blocks.json schema.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from graph_datasheet_extractor.layout_analysis.layout_models import (
    BoundingBox,
    LayoutAnalysisResult,
    LayoutBlock,
    LayoutBlockType,
    layout_analysis_result_to_dict,
    make_block_id,
)


class DolphinLayoutAnalysisError(RuntimeError):
    """Raised when Dolphin-based layout analysis fails."""


LAYOUT_BACKEND = "dolphin_adapter"


DEFAULT_RAW_OUTPUT_PATH = Path("outputs/intermediate/dolphin_raw_output.json")


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


TABLE_CUE_PATTERNS = [
    r"\btab\.\s*\d+",
    r"\btable\s*\d+",
    r"\btab\s*\d+",
    r"\btabelle\s*\d+",
]


FIGURE_CUE_PATTERNS = [
    r"\bfig\.\s*\d+",
    r"\bfigure\s+\d+",
    r"\babb\.\s*\d+",
    r"\babbildung\s+\d+",
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
    "PACKAGE DIMENSIONS",
    "BLISTER TAPE DIMENSIONS",
    "REEL DIMENSIONS",
    "Volume:",
    "pcs/reel",
]


def _configure_huggingface_token_from_env() -> None:
    """Load HF_TOKEN from .env and expose it to Hugging Face libraries.

    The project uses the standard variable name HF_TOKEN.

    Some Hugging Face related libraries also check HUGGINGFACE_HUB_TOKEN.
    If HF_TOKEN exists and HUGGINGFACE_HUB_TOKEN is not already set, this
    function maps HF_TOKEN to HUGGINGFACE_HUB_TOKEN.

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


def _load_json_file(input_path: str | Path) -> Any:
    """Load JSON from a file."""

    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"JSON file not found: {input_path}")

    try:
        return json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DolphinLayoutAnalysisError(f"Invalid JSON file: {input_path}") from exc


def _write_json_file(payload: Any, output_path: str | Path) -> Path:
    """Write JSON payload to file."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def _resolve_raw_output_path(raw_output_path: str | Path | None) -> Path:
    """Resolve Dolphin raw output path."""

    if raw_output_path is not None:
        return Path(raw_output_path)

    env_path = os.getenv("DOLPHIN_RAW_OUTPUT")
    if env_path:
        return Path(env_path)

    return DEFAULT_RAW_OUTPUT_PATH


def _run_dolphin_external_command(
    input_pdf: Path,
    raw_output_path: Path,
) -> None:
    """Run external Dolphin command if DOLPHIN_COMMAND is configured.

    DOLPHIN_COMMAND can contain placeholders:
        {input_pdf}
        {raw_output}
    """

    load_dotenv()
    command_template = os.getenv("DOLPHIN_COMMAND")

    if not command_template:
        raise DolphinLayoutAnalysisError(
            "Dolphin raw output does not exist and DOLPHIN_COMMAND is not set. "
            "Either provide an existing Dolphin raw JSON output with "
            "--raw-output, or set DOLPHIN_COMMAND in .env."
        )

    raw_output_path.parent.mkdir(parents=True, exist_ok=True)

    command = command_template.format(
        input_pdf=str(input_pdf),
        raw_output=str(raw_output_path),
    )

    try:
        completed = subprocess.run(
            shlex.split(command),
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # pragma: no cover - external command
        raise DolphinLayoutAnalysisError(
            f"Failed to execute Dolphin command: {command}"
        ) from exc

    if completed.returncode != 0:
        raise DolphinLayoutAnalysisError(
            "Dolphin command failed.\n"
            f"Command: {command}\n"
            f"Return code: {completed.returncode}\n"
            f"STDOUT:\n{completed.stdout}\n"
            f"STDERR:\n{completed.stderr}"
        )

    if not raw_output_path.exists():
        raise DolphinLayoutAnalysisError(
            "Dolphin command finished successfully, but raw output file was "
            f"not created: {raw_output_path}"
        )


def _as_text(value: Any) -> str:
    """Convert a possible text field into string."""

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (int, float, bool)):
        return str(value)

    if isinstance(value, list):
        parts = [_as_text(item) for item in value]
        return "\n".join(part for part in parts if part)

    if isinstance(value, dict):
        for key in ["text", "content", "markdown", "html", "value"]:
            if key in value:
                return _as_text(value[key])

    return ""


def _extract_text_from_element(element: dict[str, Any]) -> str:
    """Extract text/content from a flexible Dolphin-like element."""

    for key in [
        "text",
        "content",
        "markdown",
        "html",
        "recognized_text",
        "parsed_text",
        "value",
    ]:
        if key in element:
            text = _as_text(element[key])
            if text:
                return text

    return ""


def _extract_label_from_element(element: dict[str, Any]) -> str:
    """Extract layout label/type from a flexible Dolphin-like element."""

    for key in [
        "label",
        "type",
        "category",
        "class",
        "element_type",
        "block_type",
    ]:
        value = element.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return "unknown"


def _extract_page_number_from_element(
    element: dict[str, Any],
    fallback_page: int,
) -> int:
    """Extract page number from a flexible Dolphin-like element."""

    for key in ["page_number", "page", "page_idx", "page_index"]:
        if key not in element:
            continue

        try:
            value = int(element[key])
        except (TypeError, ValueError):
            continue

        # page_idx/page_index are often zero-based.
        if key in {"page_idx", "page_index"}:
            return value + 1

        return value

    return fallback_page


def _extract_order_from_element(
    element: dict[str, Any],
    fallback_order: int,
) -> int:
    """Extract reading order from a flexible Dolphin-like element."""

    for key in ["reading_order", "order", "index", "block_index"]:
        if key not in element:
            continue

        try:
            return int(element[key])
        except (TypeError, ValueError):
            continue

    return fallback_order


def _extract_bbox_from_element(element: dict[str, Any]) -> BoundingBox | None:
    """Extract bounding box from flexible Dolphin-like element."""

    bbox_value = None

    for key in ["bbox", "box", "bounding_box"]:
        if key in element:
            bbox_value = element[key]
            break

    if bbox_value is None:
        keys = {"x0", "y0", "x1", "y1"}
        if keys.issubset(element.keys()):
            try:
                return BoundingBox(
                    x0=float(element["x0"]),
                    y0=float(element["y0"]),
                    x1=float(element["x1"]),
                    y1=float(element["y1"]),
                )
            except (TypeError, ValueError):
                return None

    if isinstance(bbox_value, dict):
        try:
            return BoundingBox(
                x0=float(bbox_value.get("x0", bbox_value.get("left"))),
                y0=float(bbox_value.get("y0", bbox_value.get("top"))),
                x1=float(bbox_value.get("x1", bbox_value.get("right"))),
                y1=float(bbox_value.get("y1", bbox_value.get("bottom"))),
            )
        except (TypeError, ValueError):
            return None

    if isinstance(bbox_value, list) and len(bbox_value) >= 4:
        try:
            return BoundingBox(
                x0=float(bbox_value[0]),
                y0=float(bbox_value[1]),
                x1=float(bbox_value[2]),
                y1=float(bbox_value[3]),
            )
        except (TypeError, ValueError):
            return None

    return None


def _contains_any(text: str, terms: list[str]) -> bool:
    """Case-insensitive containment check."""

    text_lower = text.lower()
    return any(term.lower() in text_lower for term in terms)


def _matches_any_regex(text: str, patterns: list[str]) -> bool:
    """Regex pattern check."""

    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _looks_table_like(text: str, raw_label: str) -> bool:
    """Detect table-like content."""

    label_lower = raw_label.lower()
    text_upper = text.upper()

    if "table" in label_lower or "tabular" in label_lower:
        return True

    if "|" in text and "---" in text:
        return True

    if _matches_any_regex(text, TABLE_CUE_PATTERNS):
        return True

    cue_count = sum(1 for cue in TABLE_CUE_TERMS if cue.upper() in text_upper)
    if cue_count >= 3:
        return True

    return False


def _map_dolphin_label_to_block_type(
    raw_label: str,
    text: str,
) -> LayoutBlockType:
    """Map Dolphin-like label to shared LayoutBlockType."""

    label = raw_label.lower().strip()
    stripped = text.strip()

    if not stripped and not label:
        return "unknown"

    if any(term in label for term in ["title"]):
        return "title"

    if any(term in label for term in ["heading", "header", "section"]):
        return "heading"

    if any(term in label for term in ["list"]):
        return "list"

    if any(term in label for term in ["table", "tabular"]):
        return "table_like"

    if any(term in label for term in ["figure", "image", "chart", "graph"]):
        return "figure_or_graph"

    if any(term in label for term in ["caption"]):
        return "figure_caption"

    if _contains_any(stripped, LEGAL_CUE_TERMS):
        if len(stripped) < 300 and "Legal Disclaimer" not in stripped:
            return "boilerplate"
        return "legal"

    if _contains_any(stripped, PACKAGE_ONLY_CUE_TERMS):
        return "package_drawing"

    if _matches_any_regex(stripped, FIGURE_CUE_PATTERNS):
        return "figure_or_graph"

    if _looks_table_like(stripped, raw_label):
        return "table_like"

    if stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("•"):
        return "list"

    if len(stripped) < 100 and stripped.isupper():
        return "heading"

    if stripped:
        return "paragraph"

    return "unknown"


def _iter_candidate_elements(payload: Any) -> list[dict[str, Any]]:
    """Extract candidate layout elements from flexible Dolphin raw output.

    This function supports several common JSON shapes:

    1. A flat list of elements.
    2. {"elements": [...]}
    3. {"layout": [...]}
    4. {"results": [...]}
    5. {"pages": [{"page_number": 1, "elements": [...]}]}
    """

    elements: list[dict[str, Any]] = []

    def visit(value: Any, current_page: int | None = None) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item, current_page=current_page)
            return

        if not isinstance(value, dict):
            return

        page_hint = current_page

        for page_key in ["page_number", "page"]:
            if page_key in value:
                try:
                    page_hint = int(value[page_key])
                except (TypeError, ValueError):
                    pass

        for page_index_key in ["page_idx", "page_index"]:
            if page_index_key in value:
                try:
                    page_hint = int(value[page_index_key]) + 1
                except (TypeError, ValueError):
                    pass

        for key in ["elements", "layout", "blocks", "items", "detections"]:
            if isinstance(value.get(key), list):
                visit(value[key], current_page=page_hint)
                return

        for key in ["pages", "results"]:
            if isinstance(value.get(key), list):
                visit(value[key], current_page=page_hint)
                return

        # Treat as an element if it has at least a label, text, or bbox.
        has_element_signal = any(
            key in value
            for key in [
                "label",
                "type",
                "category",
                "class",
                "element_type",
                "block_type",
                "text",
                "content",
                "markdown",
                "bbox",
                "box",
                "bounding_box",
            ]
        )

        if has_element_signal:
            element = dict(value)
            if page_hint is not None and "page_number" not in element:
                element["page_number"] = page_hint
            elements.append(element)

    visit(payload)

    return elements


def _convert_dolphin_raw_to_layout_blocks(
    raw_payload: Any,
    source_file: str,
) -> list[LayoutBlock]:
    """Convert flexible Dolphin raw output to shared LayoutBlock objects."""

    candidate_elements = _iter_candidate_elements(raw_payload)

    if not candidate_elements:
        raise DolphinLayoutAnalysisError(
            "No candidate layout elements found in Dolphin raw output."
        )

    page_local_indices: dict[int, int] = {}
    blocks: list[LayoutBlock] = []

    for fallback_order, element in enumerate(candidate_elements, start=1):
        page_number = _extract_page_number_from_element(
            element,
            fallback_page=1,
        )
        page_local_indices[page_number] = page_local_indices.get(page_number, 0) + 1

        block_index = page_local_indices[page_number]
        raw_label = _extract_label_from_element(element)
        text = _extract_text_from_element(element)
        reading_order = _extract_order_from_element(element, fallback_order)
        bbox = _extract_bbox_from_element(element)

        block_type = _map_dolphin_label_to_block_type(
            raw_label=raw_label,
            text=text,
        )

        blocks.append(
            LayoutBlock(
                block_id=make_block_id(page_number, block_index),
                page_number=page_number,
                block_index=block_index,
                block_type=block_type,
                text=text,
                char_count=len(text),
                reading_order=reading_order,
                section_heading=None,
                bbox=bbox,
                metadata={
                    "source": LAYOUT_BACKEND,
                    "source_file": source_file,
                    "raw_label": raw_label,
                    "raw_element_keys": sorted(element.keys()),
                    "confidence": element.get("confidence", element.get("score")),
                },
            )
        )

    blocks.sort(key=lambda block: (block.page_number, block.reading_order, block.block_index))

    return blocks


def analyze_layout_with_dolphin(
    pdf_path: str | Path,
    raw_output_path: str | Path | None = None,
    run_if_missing: bool = True,
) -> LayoutAnalysisResult:
    """Analyze PDF layout using Dolphin raw output or an external command.

    Args:
        pdf_path: Source PDF file.
        raw_output_path: Existing or target Dolphin raw JSON output path.
        run_if_missing: If True and raw output is missing, try DOLPHIN_COMMAND.

    Returns:
        LayoutAnalysisResult mapped to the shared schema.
    """

    _configure_huggingface_token_from_env()

    pdf_path = _validate_pdf_path(pdf_path)
    resolved_raw_output_path = _resolve_raw_output_path(raw_output_path)

    if not resolved_raw_output_path.exists():
        if not run_if_missing:
            raise FileNotFoundError(
                f"Dolphin raw output not found: {resolved_raw_output_path}"
            )

        _run_dolphin_external_command(
            input_pdf=pdf_path,
            raw_output_path=resolved_raw_output_path,
        )

    raw_payload = _load_json_file(resolved_raw_output_path)

    blocks = _convert_dolphin_raw_to_layout_blocks(
        raw_payload=raw_payload,
        source_file=str(pdf_path),
    )

    if not blocks:
        raise DolphinLayoutAnalysisError(
            f"Dolphin produced no layout blocks for PDF: {pdf_path}"
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
    """Write Dolphin layout analysis result to JSON."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(layout_analysis_result_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def analyze_layout_file_with_dolphin(
    pdf_path: str | Path,
    output_path: str | Path,
    raw_output_path: str | Path | None = None,
    run_if_missing: bool = True,
) -> Path:
    """Convenience function: analyze PDF with Dolphin and write layout JSON."""

    result = analyze_layout_with_dolphin(
        pdf_path=pdf_path,
        raw_output_path=raw_output_path,
        run_if_missing=run_if_missing,
    )

    return write_layout_blocks_json(result, output_path)