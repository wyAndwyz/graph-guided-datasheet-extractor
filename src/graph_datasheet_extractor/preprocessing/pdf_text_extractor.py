"""Page-level PDF text extraction utilities.

This module implements the first step of the Phase 2 document screening
pipeline:

    PDF datasheet -> page_texts.json

It intentionally does not call an LLM. The output is a deterministic
intermediate JSON file that can later be consumed by page scoring and
content-block selection modules.

Expected output structure:

{
  "source_file": "data/raw/vishay_temt6000x01_datasheet.pdf",
  "page_count": 4,
  "extraction_method": "pypdf",
  "pages": [
    {
      "page_number": 1,
      "text": "...",
      "char_count": 1234
    }
  ]
}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExtractedPage:
    """Text extracted from one PDF page.

    Attributes:
        page_number: One-based page number, matching normal PDF reading.
        text: Extracted page text. Empty string if no text could be extracted.
        char_count: Number of characters in the extracted text.
    """

    page_number: int
    text: str
    char_count: int


@dataclass(frozen=True)
class PageTextExtractionResult:
    """Page-level text extraction result for one PDF file."""

    source_file: str
    page_count: int
    extraction_method: str
    pages: list[ExtractedPage]


class PDFTextExtractionError(RuntimeError):
    """Raised when PDF text extraction fails."""


def _normalize_page_text(text: str | None) -> str:
    """Normalize extracted page text.

    The goal is conservative normalization, not aggressive cleaning.
    Page scoring may still need line breaks and original local context.
    """

    if text is None:
        return ""

    # Normalize Windows and old Mac line endings.
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip excessive leading/trailing whitespace but preserve internal lines.
    normalized = normalized.strip()

    return normalized


def extract_page_texts(pdf_path: str | Path) -> PageTextExtractionResult:
    """Extract page-level text from a local PDF file.

    Args:
        pdf_path: Path to a local PDF file.

    Returns:
        PageTextExtractionResult with one ExtractedPage per PDF page.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        ValueError: If the path does not point to a PDF file.
        PDFTextExtractionError: If the PDF cannot be read by pypdf.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if not pdf_path.is_file():
        raise ValueError(f"Expected a file path, got: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {pdf_path}")

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PDFTextExtractionError(
            "Missing dependency 'pypdf'. Install it with: pip install pypdf"
        ) from exc

    try:
        reader = PdfReader(str(pdf_path))
        pages: list[ExtractedPage] = []

        for index, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text()
            text = _normalize_page_text(raw_text)
            pages.append(
                ExtractedPage(
                    page_number=index,
                    text=text,
                    char_count=len(text),
                )
            )

        return PageTextExtractionResult(
            source_file=str(pdf_path),
            page_count=len(pages),
            extraction_method="pypdf",
            pages=pages,
        )

    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise PDFTextExtractionError(
            f"Failed to extract text from PDF: {pdf_path}"
        ) from exc


def extraction_result_to_dict(
    result: PageTextExtractionResult,
) -> dict[str, Any]:
    """Convert a PageTextExtractionResult into a JSON-serializable dict."""

    return {
        "source_file": result.source_file,
        "page_count": result.page_count,
        "extraction_method": result.extraction_method,
        "pages": [asdict(page) for page in result.pages],
    }


def write_page_texts_json(
    result: PageTextExtractionResult,
    output_path: str | Path,
) -> Path:
    """Write page-level text extraction result to JSON.

    Args:
        result: Extraction result returned by extract_page_texts.
        output_path: Target JSON path.

    Returns:
        The written output path.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = extraction_result_to_dict(result)

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def extract_pdf_to_page_texts_json(
    pdf_path: str | Path,
    output_path: str | Path,
) -> Path:
    """Convenience function: extract PDF page texts and write JSON output."""

    result = extract_page_texts(pdf_path)
    return write_page_texts_json(result, output_path)
