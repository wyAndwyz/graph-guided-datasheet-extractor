"""LLM-based page scoring for datasheet document screening.

This module implements the LLM-assisted page scorer for Phase 2.

Input:
    outputs/intermediate/page_texts.json

Output:
    outputs/intermediate/page_scores_llm_based.json

The scorer asks an LLM to judge whether each page is relevant for later
technical information extraction. It does not extract parameters yet.

Design principle:
- The LLM output is treated as an assisted scoring result, not as trusted logic.
- The output is structured with Pydantic.
- The result can later be compared with the rule-based scorer.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError


RelevanceLevel = Literal["high", "medium", "low", "irrelevant"]


@dataclass(frozen=True)
class LLMPageScore:
    """LLM-assisted relevance score for one page."""

    page_number: int
    score: float
    relevance_level: str
    char_count: int
    useful_for_extraction: bool
    likely_content_type: str
    extraction_targets_found: list[str]
    reasoning: str


@dataclass(frozen=True)
class LLMBasedPageScoringResult:
    """LLM-based page scoring result for one extracted PDF document."""

    source_file: str
    scoring_method: str
    llm_model: str
    page_count: int
    pages: list[LLMPageScore]


class LLMPageScoringError(RuntimeError):
    """Raised when LLM-based page scoring fails."""


class LLMPageScoreModel(BaseModel):
    """Structured output schema for one LLM-scored page."""

    score: float = Field(
        ge=0,
        le=100,
        description="Relevance score from 0 to 100.",
    )
    relevance_level: RelevanceLevel = Field(
        description="Coarse relevance level for later extraction."
    )
    useful_for_extraction: bool = Field(
        description="Whether this page should be considered for later extraction."
    )
    likely_content_type: str = Field(
        description=(
            "Short label describing the page content, for example "
            "'technical summary', 'electrical characteristics', "
            "'package dimensions', 'packaging information', or 'legal disclaimer'."
        )
    )
    extraction_targets_found: list[str] = Field(
        default_factory=list,
        description=(
            "Technical extraction targets or concepts likely present on this page, "
            "for example 'dimensions', 'operating temperature', 'peak wavelength'."
        ),
    )
    reasoning: str = Field(
        description="Brief explanation of why the page received this score."
    )


class PageTextPayload(BaseModel):
    """Minimal validation model for one page from page_texts.json."""

    page_number: int
    text: str = ""
    char_count: int = 0


def load_page_texts_json(input_path: str | Path) -> dict[str, Any]:
    """Load page-level text extraction JSON."""

    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Page texts JSON not found: {input_path}")

    try:
        return json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LLMPageScoringError(f"Invalid JSON file: {input_path}") from exc


def _truncate_page_text(text: str, max_chars: int = 3500) -> str:
    """Truncate long page text to keep the page-scoring prompt compact."""

    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n\n[TRUNCATED]"


def _build_page_scoring_prompt(page: PageTextPayload) -> str:
    """Build the prompt for LLM-assisted page scoring."""

    page_text = _truncate_page_text(page.text)

    return f"""
You are scoring one page from a technical electronic/sensor datasheet.

Task:
Decide how relevant this page is for later structured technical information extraction.

The target extraction scope includes:
- product/equipment identity
- equipment type
- package type and package form
- physical dimensions
- electrical or optical technical parameters
- operating/storage/soldering temperature
- wavelength, sensitivity, angle, voltage, current, power, capacitance
- units and evidence text

Do not extract the full parameter table.
Only score the page for relevance.

Scoring guidance:
- 90-100: very important technical parameter page, should definitely be used
- 70-89: important technical page, should be used
- 40-69: partially useful page, may be used depending on target
- 10-39: weakly useful page
- 0-9: irrelevant for technical extraction

Relevance level guidance:
- high: central technical content for extraction
- medium: useful but secondary technical content
- low: only weakly useful
- irrelevant: legal, ordering-only, packaging-only, or unrelated content

Important:
- Legal disclaimer pages should usually be irrelevant.
- Tape/reel/blister packaging pages should usually be irrelevant unless package dimensions of the component itself are present.
- A page with package dimensions of the component can be medium or high depending on usefulness.
- Graph/curve pages can be medium or high if they contain technical characteristics useful for extraction.

Page number:
{page.page_number}

Page character count:
{page.char_count}

Page text:
---
{page_text}
---
""".strip()


def _get_llm(model_name: str):
    """Create a LangChain chat model instance.

    The API key is expected to be provided through environment variables,
    typically OPENAI_API_KEY in the local .env file.
    """

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise LLMPageScoringError(
            "Missing dependency 'langchain-openai'. "
            "Install it with: pip install langchain-openai"
        ) from exc

    return ChatOpenAI(model=model_name, temperature=0)


def score_single_page_with_llm(
    page_payload: dict[str, Any],
    model_name: str = "gpt-4o-mini",
) -> LLMPageScore:
    """Score one page using an LLM with structured output."""

    try:
        page = PageTextPayload.model_validate(page_payload)
    except ValidationError as exc:
        raise LLMPageScoringError(
            f"Invalid page payload: {page_payload}"
        ) from exc

    llm = _get_llm(model_name)
    structured_llm = llm.with_structured_output(LLMPageScoreModel)

    prompt = _build_page_scoring_prompt(page)

    try:
        llm_result = structured_llm.invoke(prompt)
    except Exception as exc:  # pragma: no cover - external API failure
        raise LLMPageScoringError(
            f"LLM page scoring failed for page {page.page_number}"
        ) from exc

    if not isinstance(llm_result, LLMPageScoreModel):
        try:
            llm_result = LLMPageScoreModel.model_validate(llm_result)
        except ValidationError as exc:
            raise LLMPageScoringError(
                f"Invalid structured LLM result for page {page.page_number}"
            ) from exc

    return LLMPageScore(
        page_number=page.page_number,
        score=round(float(llm_result.score), 2),
        relevance_level=llm_result.relevance_level,
        char_count=page.char_count,
        useful_for_extraction=llm_result.useful_for_extraction,
        likely_content_type=llm_result.likely_content_type,
        extraction_targets_found=llm_result.extraction_targets_found,
        reasoning=llm_result.reasoning,
    )


def score_pages_llm_based(
    page_texts_payload: dict[str, Any],
    model_name: str = "gpt-4o-mini",
) -> LLMBasedPageScoringResult:
    """Score all pages from a page_texts.json payload using an LLM."""

    source_file = str(page_texts_payload.get("source_file", ""))
    pages_payload = page_texts_payload.get("pages", [])

    if not isinstance(pages_payload, list):
        raise LLMPageScoringError("Expected 'pages' to be a list.")

    page_scores: list[LLMPageScore] = []

    for page_payload in pages_payload:
        page_score = score_single_page_with_llm(
            page_payload=page_payload,
            model_name=model_name,
        )
        page_scores.append(page_score)

    return LLMBasedPageScoringResult(
        source_file=source_file,
        scoring_method="llm_based_v1",
        llm_model=model_name,
        page_count=len(page_scores),
        pages=page_scores,
    )


def scoring_result_to_dict(result: LLMBasedPageScoringResult) -> dict[str, Any]:
    """Convert LLM scoring result to a JSON-serializable dictionary."""

    return {
        "source_file": result.source_file,
        "scoring_method": result.scoring_method,
        "llm_model": result.llm_model,
        "page_count": result.page_count,
        "pages": [asdict(page) for page in result.pages],
    }


def write_page_scores_json(
    result: LLMBasedPageScoringResult,
    output_path: str | Path,
) -> Path:
    """Write LLM-based page scores to JSON."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(scoring_result_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def score_page_texts_file_llm_based(
    input_path: str | Path,
    output_path: str | Path,
    model_name: str = "gpt-4o-mini",
) -> Path:
    """Convenience function: load page_texts.json, score pages, and write output."""

    payload = load_page_texts_json(input_path)
    result = score_pages_llm_based(payload, model_name=model_name)
    return write_page_scores_json(result, output_path)