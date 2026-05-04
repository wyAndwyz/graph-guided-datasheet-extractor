"""Rule-based page scoring for datasheet document screening.

This module implements the deterministic baseline scorer for Phase 2.

Input:
    outputs/intermediate/page_texts.json

Output:
    outputs/intermediate/page_scores_rule_based.json

The scorer uses transparent local rules:
- positive matches for product model, equipment type, parameter labels, aliases, units, and table/section cues;
- negative matches for legal/disclaimer/order-only/reel-only pages;
- page-level relevance classification.

No LLM is called here.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ScoringTerm:
    """A weighted term used for rule-based page scoring."""

    term: str
    weight: float
    category: str
    match_mode: str = "case_insensitive"


@dataclass(frozen=True)
class PageScore:
    """Rule-based relevance score for one page."""

    page_number: int
    score: float
    relevance_level: str
    char_count: int
    matched_terms: list[str]
    matched_categories: list[str]
    positive_reasons: list[str]
    negative_reasons: list[str]


@dataclass(frozen=True)
class RuleBasedPageScoringResult:
    """Rule-based page scoring result for one extracted PDF document."""

    source_file: str
    scoring_method: str
    page_count: int
    pages: list[PageScore]


class RuleBasedPageScoringError(RuntimeError):
    """Raised when rule-based page scoring fails."""


DEFAULT_POSITIVE_TERMS: list[ScoringTerm] = [
    # Product / equipment identity
    ScoringTerm("TEMT6000X01", 5.0, "product_model"),
    ScoringTerm("ambient light sensor", 4.0, "equipment_type"),
    ScoringTerm("phototransistor", 2.0, "equipment_type"),
    ScoringTerm("Vishay Semiconductors", 1.0, "manufacturer"),
    # Important sections
    ScoringTerm("DESCRIPTION", 2.0, "section_heading"),
    ScoringTerm("FEATURES", 2.0, "section_heading"),
    ScoringTerm("PRODUCT SUMMARY", 3.0, "section_heading"),
    ScoringTerm("ABSOLUTE MAXIMUM RATINGS", 3.0, "section_heading"),
    ScoringTerm("BASIC CHARACTERISTICS", 4.0, "section_heading"),
    ScoringTerm("PACKAGE DIMENSIONS", 3.0, "section_heading"),
    # Parameter labels / aliases
    ScoringTerm("Dimensions", 3.0, "parameter_type"),
    ScoringTerm("Package form", 2.0, "parameter_type"),
    ScoringTerm("Package type", 2.0, "parameter_type"),
    ScoringTerm("Angle of half sensitivity", 4.0, "parameter_type"),
    ScoringTerm("Wavelength of peak sensitivity", 4.0, "parameter_type"),
    ScoringTerm("Range of spectral bandwidth", 4.0, "parameter_type"),
    ScoringTerm("Collector emitter voltage", 3.0, "parameter_type"),
    ScoringTerm("Emitter collector voltage", 3.0, "parameter_type"),
    ScoringTerm("Collector current", 3.0, "parameter_type"),
    ScoringTerm("Power dissipation", 3.0, "parameter_type"),
    ScoringTerm("Operating temperature range", 4.0, "parameter_type"),
    ScoringTerm("Storage temperature range", 3.0, "parameter_type"),
    ScoringTerm("Soldering temperature", 2.0, "parameter_type"),
    ScoringTerm("Collector light current", 3.0, "parameter_type"),
    ScoringTerm("Collector dark current", 2.0, "parameter_type"),
    ScoringTerm("Collector emitter capacitance", 2.0, "parameter_type"),
    # Symbols often used in this datasheet
    ScoringTerm(r"\bVCEO\b", 2.0, "symbol", "regex"),
    ScoringTerm(r"\bVECO\b", 2.0, "symbol", "regex"),
    ScoringTerm(r"\bIC\b", 1.0, "symbol", "regex"),
    ScoringTerm(r"\bPV\b", 1.0, "symbol", "regex"),
    ScoringTerm("Tamb", 1.5, "symbol"),
    ScoringTerm("IPCE", 2.0, "symbol"),
    ScoringTerm("λp", 2.0, "symbol"),
    ScoringTerm("λ0.5", 2.0, "symbol"),
    ScoringTerm("φ", 1.5, "symbol"),
    ScoringTerm("", 1.5, "symbol"),
    # Unit cues
    ScoringTerm("mm", 1.0, "unit"),
    ScoringTerm("nm", 1.0, "unit"),
    ScoringTerm("deg", 1.0, "unit"),
    ScoringTerm("°C", 1.0, "unit"),
    ScoringTerm(r"\bV\b", 0.8, "unit", "regex"),
    ScoringTerm(r"\bmA\b", 0.8, "unit", "regex"),
    ScoringTerm("μA", 0.8, "unit"),
    ScoringTerm("µA", 0.8, "unit"),
    ScoringTerm("mW", 0.8, "unit"),
    ScoringTerm("pF", 0.8, "unit"),
    # Table cues
    ScoringTerm("PARAMETER", 2.0, "table_cue"),
    ScoringTerm("TEST CONDITION", 1.5, "table_cue"),
    ScoringTerm("SYMBOL", 1.5, "table_cue"),
    ScoringTerm("VALUE", 1.0, "table_cue"),
    ScoringTerm("UNIT", 1.5, "table_cue"),
    ScoringTerm("MIN.", 1.0, "table_cue"),
    ScoringTerm("TYP.", 1.0, "table_cue"),
    ScoringTerm("MAX.", 1.0, "table_cue"),
]

DEFAULT_NEGATIVE_TERMS: list[ScoringTerm] = [
    ScoringTerm("Legal Disclaimer", -8.0, "legal_disclaimer"),
    ScoringTerm("Disclaimer", -1.0, "legal_disclaimer"),
    ScoringTerm("ALL RIGHTS RESERVED", -5.0, "legal_disclaimer"),
    ScoringTerm("liability", -3.0, "legal_disclaimer"),
    ScoringTerm("warranty", -3.0, "legal_disclaimer"),
    ScoringTerm("third-party websites", -3.0, "legal_disclaimer"),
    ScoringTerm("No license", -3.0, "legal_disclaimer"),
    ScoringTerm("BLISTER TAPE DIMENSIONS", -2.0, "packaging_only"),
    ScoringTerm("REEL DIMENSIONS", -2.0, "packaging_only"),
    ScoringTerm("Volume: 3000 pcs/reel", -2.0, "packaging_only"),
    ScoringTerm("ORDERING INFORMATION", -1.0, "ordering"),
    ScoringTerm("MOQ", -1.0, "ordering"),
]


def load_page_texts_json(input_path: str | Path) -> dict[str, Any]:
    """Load page-level text extraction JSON."""

    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Page texts JSON not found: {input_path}")

    try:
        return json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuleBasedPageScoringError(
            f"Invalid JSON file: {input_path}"
        ) from exc


def _normalize_for_matching(text: str) -> str:
    """Normalize text for robust case-insensitive matching."""

    return text.lower()


def _term_matches(text: str, normalized_text: str, term: ScoringTerm) -> bool:
    """Return whether a scoring term matches a page text."""

    if term.match_mode == "case_sensitive":
        return term.term in text

    if term.match_mode == "case_insensitive":
        return term.term.lower() in normalized_text

    if term.match_mode == "regex":
        return re.search(term.term, text, flags=re.IGNORECASE | re.MULTILINE) is not None

    raise ValueError(f"Unsupported match_mode: {term.match_mode}")


def _score_to_relevance_level(score: float) -> str:
    """Convert numeric score to a coarse relevance level."""

    if score >= 20:
        return "high"
    if score >= 10:
        return "medium"
    if score >= 3:
        return "low"
    return "irrelevant"


def score_single_page(
    page: dict[str, Any],
    positive_terms: list[ScoringTerm] | None = None,
    negative_terms: list[ScoringTerm] | None = None,
) -> PageScore:
    """Score one extracted page using deterministic rules."""

    positive_terms = positive_terms or DEFAULT_POSITIVE_TERMS
    negative_terms = negative_terms or DEFAULT_NEGATIVE_TERMS

    page_number = int(page["page_number"])
    text = str(page.get("text", ""))
    char_count = int(page.get("char_count", len(text)))

    normalized_text = _normalize_for_matching(text)

    score = 0.0
    matched_terms: list[str] = []
    matched_categories: list[str] = []
    positive_reasons: list[str] = []
    negative_reasons: list[str] = []

    for term in positive_terms:
        if _term_matches(text, normalized_text, term):
            score += term.weight
            matched_terms.append(term.term)
            matched_categories.append(term.category)
            positive_reasons.append(
                f"+{term.weight:g}: matched {term.category} term '{term.term}'"
            )

    for term in negative_terms:
        if _term_matches(text, normalized_text, term):
            score += term.weight
            matched_terms.append(term.term)
            matched_categories.append(term.category)
            negative_reasons.append(
                f"{term.weight:g}: matched {term.category} term '{term.term}'"
            )

    # Conservative guard: a page with almost no extracted text is not useful.
    if char_count < 100:
        score -= 3.0
        negative_reasons.append("-3: very short extracted text")

    # Avoid negative final scores for easier interpretation.
    score = max(score, 0.0)

    # Keep categories unique but deterministic.
    unique_categories = sorted(set(matched_categories))

    return PageScore(
        page_number=page_number,
        score=round(score, 2),
        relevance_level=_score_to_relevance_level(score),
        char_count=char_count,
        matched_terms=matched_terms,
        matched_categories=unique_categories,
        positive_reasons=positive_reasons,
        negative_reasons=negative_reasons,
    )


def score_pages_rule_based(page_texts_payload: dict[str, Any]) -> RuleBasedPageScoringResult:
    """Score all pages from a page_texts.json payload."""

    source_file = str(page_texts_payload.get("source_file", ""))
    pages_payload = page_texts_payload.get("pages", [])

    if not isinstance(pages_payload, list):
        raise RuleBasedPageScoringError("Expected 'pages' to be a list.")

    page_scores = [score_single_page(page) for page in pages_payload]

    return RuleBasedPageScoringResult(
        source_file=source_file,
        scoring_method="rule_based_v1",
        page_count=len(page_scores),
        pages=page_scores,
    )


def scoring_result_to_dict(result: RuleBasedPageScoringResult) -> dict[str, Any]:
    """Convert scoring result to a JSON-serializable dictionary."""

    return {
        "source_file": result.source_file,
        "scoring_method": result.scoring_method,
        "page_count": result.page_count,
        "pages": [asdict(page) for page in result.pages],
    }


def write_page_scores_json(
    result: RuleBasedPageScoringResult,
    output_path: str | Path,
) -> Path:
    """Write rule-based page scores to JSON."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(scoring_result_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def score_page_texts_file_rule_based(
    input_path: str | Path,
    output_path: str | Path,
) -> Path:
    """Convenience function: load page_texts.json, score pages, and write output."""

    payload = load_page_texts_json(input_path)
    result = score_pages_rule_based(payload)
    return write_page_scores_json(result, output_path)