from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from graph_datasheet_extractor.graph_representation.graph_models import (
    GraphExtraction,
    GraphRelationship,
)


class GraphJsonValidationResult(dict):
    """Dictionary-like validation result for graph-shaped JSON."""


def load_graph_extraction_json(path: str | Path) -> GraphExtraction:
    """Load and parse a graph-shaped JSON file into a GraphExtraction model."""
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Graph extraction JSON file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return GraphExtraction.model_validate(data)


def _relationship_key(relationship: GraphRelationship) -> tuple[str, str, str]:
    """Create a stable key for checking duplicated relationships."""
    if relationship.target is not None:
        target_repr = f"target:{relationship.target}"
    elif relationship.target_ref is not None:
        target_repr = (
            f"target_ref:{relationship.target_ref.label}:"
            f"{relationship.target_ref.key}:{relationship.target_ref.value}"
        )
    else:
        target_repr = "target:none"

    return relationship.source, relationship.type, target_repr


def _get_relationship_targets_by_source_and_type(
    extraction: GraphExtraction,
    source_id: str,
    relationship_type: str,
) -> list[GraphRelationship]:
    """Return all relationships of a given type from a given source node."""
    return [
        relationship
        for relationship in extraction.relationships
        if relationship.source == source_id and relationship.type == relationship_type
    ]


def _has_relationship_type_from_source(
    extraction: GraphExtraction,
    source_id: str,
    relationship_type: str,
) -> bool:
    """Return True if source node has at least one relationship of the given type."""
    return bool(
        _get_relationship_targets_by_source_and_type(
            extraction=extraction,
            source_id=source_id,
            relationship_type=relationship_type,
        )
    )


def validate_no_duplicate_relationships(
    extraction: GraphExtraction,
    errors: list[str],
) -> None:
    """Check that relationships are not duplicated."""
    seen: set[tuple[str, str, str]] = set()

    for relationship in extraction.relationships:
        key = _relationship_key(relationship)

        if key in seen:
            errors.append(
                f"Duplicate relationship found: source={relationship.source}, "
                f"type={relationship.type}, target={key[2]}"
            )

        seen.add(key)


def validate_required_topology(
    extraction: GraphExtraction,
    errors: list[str],
) -> None:
    """Check core topology rules for graph-shaped extraction output."""
    datasheet_nodes = extraction.get_nodes_by_label("Datasheet")
    equipment_nodes = extraction.get_nodes_by_label("Equipment")
    technical_parameter_nodes = extraction.get_nodes_by_label("TechnicalParameter")
    evidence_nodes = extraction.get_nodes_by_label("Evidence")
    extraction_run_nodes = extraction.get_nodes_by_label("ExtractionRun")

    if not datasheet_nodes:
        errors.append("At least one Datasheet node is required.")

    if not equipment_nodes:
        errors.append("At least one Equipment node is required.")

    if not technical_parameter_nodes:
        errors.append("At least one TechnicalParameter node is required.")

    if not evidence_nodes:
        errors.append("At least one Evidence node is required.")

    if not extraction_run_nodes:
        errors.append("At least one ExtractionRun node is required.")

    for datasheet_node in datasheet_nodes:
        if not _has_relationship_type_from_source(
            extraction, datasheet_node.id, "DESCRIBES"
        ):
            errors.append(
                f"Datasheet node '{datasheet_node.id}' has no DESCRIBES relationship."
            )

    for equipment_node in equipment_nodes:
        if not _has_relationship_type_from_source(
            extraction, equipment_node.id, "HAS_PARAMETER"
        ):
            errors.append(
                f"Equipment node '{equipment_node.id}' has no HAS_PARAMETER relationship."
            )


def validate_technical_parameter_rules(
    extraction: GraphExtraction,
    errors: list[str],
) -> None:
    """Check required relationships for every TechnicalParameter node."""
    technical_parameter_nodes = extraction.get_nodes_by_label("TechnicalParameter")

    for parameter_node in technical_parameter_nodes:
        parameter_id = parameter_node.id

        if not _has_relationship_type_from_source(
            extraction, parameter_id, "HAS_PARAMETER_TYPE"
        ):
            errors.append(
                f"TechnicalParameter '{parameter_id}' has no HAS_PARAMETER_TYPE relationship."
            )

        if not _has_relationship_type_from_source(
            extraction, parameter_id, "EVIDENCED_BY"
        ):
            errors.append(
                f"TechnicalParameter '{parameter_id}' has no EVIDENCED_BY relationship."
            )

        if not _has_relationship_type_from_source(
            extraction, parameter_id, "GENERATED_BY"
        ):
            errors.append(
                f"TechnicalParameter '{parameter_id}' has no GENERATED_BY relationship."
            )


def validate_target_ref_rules(
    extraction: GraphExtraction,
    errors: list[str],
) -> None:
    """Check target_ref usage for vocabulary-grounding relationships.

    This validator only checks the JSON structure and expected label/key
    conventions. It does not check whether the target_ref actually exists in
    Neo4j. That will be handled by the graph loader or Neo4j-backed validation.
    """
    expected_target_ref_rules = {
        "HAS_PARAMETER_TYPE": ("ParameterType", "name"),
        "HAS_UNIT": ("Unit", "symbol"),
        "HAS_EQUIPMENT_TYPE": ("EquipmentType", "name"),
    }

    for relationship in extraction.relationships:
        if relationship.type not in expected_target_ref_rules:
            continue

        expected_label, expected_key = expected_target_ref_rules[relationship.type]

        if relationship.target_ref is None:
            errors.append(
                f"Relationship '{relationship.type}' from '{relationship.source}' "
                f"should use target_ref instead of local target."
            )
            continue

        actual_label = relationship.target_ref.label
        actual_key = relationship.target_ref.key

        if actual_label != expected_label or actual_key != expected_key:
            errors.append(
                f"Relationship '{relationship.type}' from '{relationship.source}' "
                f"has invalid target_ref. Expected label/key "
                f"({expected_label}, {expected_key}), got ({actual_label}, {actual_key})."
            )


def validate_evidence_properties(
    extraction: GraphExtraction,
    errors: list[str],
) -> None:
    """Check MVP-required properties for Evidence nodes."""
    required_properties = [
        "source_document_id",
        "page_number",
        "source_text",
        "evidence_status",
        "confidence",
    ]

    allowed_evidence_status = {
        "explicit",
        "inferred",
        "missing",
        "ambiguous",
    }

    for evidence_node in extraction.get_nodes_by_label("Evidence"):
        properties = evidence_node.properties

        for property_name in required_properties:
            if property_name not in properties:
                errors.append(
                    f"Evidence node '{evidence_node.id}' is missing required property "
                    f"'{property_name}'."
                )

        evidence_status = properties.get("evidence_status")
        if evidence_status is not None and evidence_status not in allowed_evidence_status:
            errors.append(
                f"Evidence node '{evidence_node.id}' has invalid evidence_status "
                f"'{evidence_status}'. Allowed values: {sorted(allowed_evidence_status)}."
            )

        confidence = properties.get("confidence")
        if confidence is not None:
            if not isinstance(confidence, int | float):
                errors.append(
                    f"Evidence node '{evidence_node.id}' has non-numeric confidence."
                )
            elif confidence < 0 or confidence > 1:
                errors.append(
                    f"Evidence node '{evidence_node.id}' has confidence outside [0, 1]."
                )


def validate_technical_parameter_properties(
    extraction: GraphExtraction,
    errors: list[str],
) -> None:
    """Check recommended MVP properties for TechnicalParameter nodes."""
    recommended_properties = [
        "raw_label",
        "value",
        "value_type",
    ]

    for parameter_node in extraction.get_nodes_by_label("TechnicalParameter"):
        properties = parameter_node.properties

        for property_name in recommended_properties:
            if property_name not in properties:
                errors.append(
                    f"TechnicalParameter node '{parameter_node.id}' is missing "
                    f"recommended MVP property '{property_name}'."
                )


def validate_graph_extraction(extraction: GraphExtraction) -> dict[str, Any]:
    """Run semantic validation checks on a GraphExtraction object.

    This function assumes that Pydantic structural validation has already passed.
    It checks additional graph-shaped JSON rules that are specific to this project.
    """
    errors: list[str] = []

    validate_no_duplicate_relationships(extraction, errors)
    validate_required_topology(extraction, errors)
    validate_technical_parameter_rules(extraction, errors)
    validate_target_ref_rules(extraction, errors)
    validate_evidence_properties(extraction, errors)
    validate_technical_parameter_properties(extraction, errors)

    return {
        "validation_type": "graph_shaped_json_validation",
        "passed": len(errors) == 0,
        "summary": {
            "error_count": len(errors),
            "node_count": len(extraction.nodes),
            "relationship_count": len(extraction.relationships),
            "technical_parameter_count": len(
                extraction.get_nodes_by_label("TechnicalParameter")
            ),
            "evidence_count": len(extraction.get_nodes_by_label("Evidence")),
        },
        "errors": errors,
    }


def validate_graph_extraction_file(path: str | Path) -> dict[str, Any]:
    """Load and validate a graph-shaped JSON file."""
    try:
        extraction = load_graph_extraction_json(path)
    except ValidationError as exc:
        return {
            "validation_type": "graph_shaped_json_validation",
            "passed": False,
            "summary": {
                "error_count": len(exc.errors()),
                "node_count": None,
                "relationship_count": None,
                "technical_parameter_count": None,
                "evidence_count": None,
            },
            "errors": exc.errors(),
        }
    except Exception as exc:
        return {
            "validation_type": "graph_shaped_json_validation",
            "passed": False,
            "summary": {
                "error_count": 1,
                "node_count": None,
                "relationship_count": None,
                "technical_parameter_count": None,
                "evidence_count": None,
            },
            "errors": [str(exc)],
        }

    return validate_graph_extraction(extraction)


def write_validation_report(
    report: dict[str, Any],
    output_path: str | Path,
) -> None:
    """Write graph JSON validation report to disk."""
    file_path = Path(output_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    file_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )