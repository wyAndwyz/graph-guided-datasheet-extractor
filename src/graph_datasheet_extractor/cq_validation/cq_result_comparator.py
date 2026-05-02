from __future__ import annotations

import json
from typing import Any


def _to_json_safe_value(value: Any) -> Any:
    """Convert Neo4j/Python values into JSON-serializable values.

    LLM-generated Cypher queries may accidentally return Neo4j Node,
    Relationship, or Path objects instead of scalar properties. These objects
    are not directly JSON serializable. This function prevents the validation
    report from crashing and makes such outputs visible in the report.
    """
    if value is None:
        return None

    if isinstance(value, str | int | float | bool):
        return value

    if isinstance(value, list):
        return [_to_json_safe_value(item) for item in value]

    if isinstance(value, tuple):
        return [_to_json_safe_value(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): _to_json_safe_value(inner_value)
            for key, inner_value in value.items()
        }

    # Neo4j Node objects usually expose labels and items().
    if hasattr(value, "labels") and hasattr(value, "items"):
        try:
            return {
                "_neo4j_object_type": "Node",
                "labels": sorted(list(value.labels)),
                "properties": {
                    str(key): _to_json_safe_value(inner_value)
                    for key, inner_value in dict(value.items()).items()
                },
            }
        except Exception:
            return str(value)

    # Neo4j Relationship objects usually expose type and items().
    if hasattr(value, "type") and hasattr(value, "items"):
        try:
            return {
                "_neo4j_object_type": "Relationship",
                "type": value.type,
                "properties": {
                    str(key): _to_json_safe_value(inner_value)
                    for key, inner_value in dict(value.items()).items()
                },
            }
        except Exception:
            return str(value)

    # Last-resort conversion. This keeps the report writable.
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        return str(value)


def _normalize_value(value: Any) -> Any:
    """Normalize values for stable comparison."""
    value = _to_json_safe_value(value)

    if isinstance(value, dict):
        return {key: _normalize_value(value[key]) for key in sorted(value.keys())}

    if isinstance(value, list):
        return [_normalize_value(item) for item in value]

    return value


def _sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort result rows by their JSON-like string representation."""
    normalized_rows = [_normalize_value(row) for row in rows]
    return sorted(normalized_rows, key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))


def normalize_cq_result(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize CQ query result rows for deterministic comparison."""
    return _sort_rows(rows)


def compare_cq_result(
    check_id: str,
    actual_rows: list[dict[str, Any]],
    expected_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare actual CQ query rows with expected CQ rows."""
    actual_normalized = normalize_cq_result(actual_rows)
    expected_normalized = normalize_cq_result(expected_rows)

    passed = actual_normalized == expected_normalized

    return {
        "check_id": check_id,
        "passed": passed,
        "actual": actual_normalized,
        "expected": expected_normalized,
    }