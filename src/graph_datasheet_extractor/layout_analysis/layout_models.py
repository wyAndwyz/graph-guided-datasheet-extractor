"""Shared layout analysis data models.

This module defines the common intermediate representation used by the
layout analysis layer.

The goal is to keep downstream steps independent from a specific layout
backend such as pypdf, Docling, Dolphin, MinerU, or OCR-based parsers.

Expected output file:

    outputs/intermediate/layout_blocks.json
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


LayoutBlockType = Literal[
    "title",
    "heading",
    "paragraph",
    "list",
    "table_like",
    "figure_caption",
    "figure_or_graph",
    "package_drawing",
    "boilerplate",
    "legal",
    "unknown",
]


@dataclass(frozen=True)
class BoundingBox:
    """Optional bounding box for a layout block.

    For the lightweight pypdf baseline, bounding boxes are usually unavailable
    and therefore represented as None in LayoutBlock.

    Future layout backends may populate this field.
    """

    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class LayoutBlock:
    """One layout-aware content block."""

    block_id: str
    page_number: int
    block_index: int
    block_type: LayoutBlockType
    text: str
    char_count: int
    reading_order: int
    section_heading: str | None = None
    bbox: BoundingBox | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LayoutAnalysisResult:
    """Full layout analysis result for one document."""

    source_file: str
    layout_backend: str
    page_count: int
    blocks: list[LayoutBlock]


def layout_block_to_dict(block: LayoutBlock) -> dict[str, Any]:
    """Convert a LayoutBlock to a JSON-serializable dictionary."""

    data = asdict(block)

    if block.bbox is None:
        data["bbox"] = None

    return data


def layout_analysis_result_to_dict(result: LayoutAnalysisResult) -> dict[str, Any]:
    """Convert LayoutAnalysisResult to a JSON-serializable dictionary."""

    return {
        "source_file": result.source_file,
        "layout_backend": result.layout_backend,
        "page_count": result.page_count,
        "blocks": [layout_block_to_dict(block) for block in result.blocks],
    }


def make_block_id(page_number: int, block_index: int) -> str:
    """Create a stable local block id.

    Example:
        page_1_block_001
    """

    return f"page_{page_number}_block_{block_index:03d}"