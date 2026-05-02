from __future__ import annotations

from typing import Any


def _sorted_list(values: list[Any]) -> list[Any]:
    """Sort values by their string representation for stable comparison."""
    return sorted(values, key=lambda item: str(item))


def _normalize_string_list(rows: list[dict[str, Any]], column: str) -> list[str]:
    values = [row[column] for row in rows if row.get(column) is not None]
    return _sorted_list(values)


def _normalize_allowed_units(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}

    for row in rows:
        parameter_type = row.get("parameter_type")
        allowed_units = row.get("allowed_units", [])

        if parameter_type is None:
            continue

        if allowed_units is None:
            allowed_units = []

        result[parameter_type] = _sorted_list(list(allowed_units))

    return dict(sorted(result.items()))


def _normalize_required_parameters(rows: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}

    for row in rows:
        required_parameter = row.get("required_parameter")
        parameter_type = row.get("parameter_type")

        if required_parameter is None or parameter_type is None:
            continue

        result[required_parameter] = parameter_type

    return dict(sorted(result.items()))


def _normalize_relationship_definitions(rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}

    for row in rows:
        relationship = row.get("relationship")
        from_concept = row.get("from_concept")
        to_concept = row.get("to_concept")

        if relationship is None or from_concept is None or to_concept is None:
            continue

        result[relationship] = {
            "from": from_concept,
            "to": to_concept,
        }

    return dict(sorted(result.items()))


def normalize_actual_result(check_id: str, rows: list[dict[str, Any]]) -> Any:
    """Normalize Neo4j query result rows according to the validation check."""
    if check_id == "parameter_type_vocabulary":
        return _normalize_string_list(rows, "parameter_type")

    if check_id == "unit_vocabulary":
        return _normalize_string_list(rows, "unit")

    if check_id == "equipment_type_vocabulary":
        return _normalize_string_list(rows, "equipment_type")

    if check_id == "allowed_units":
        return _normalize_allowed_units(rows)

    if check_id == "required_parameters":
        return _normalize_required_parameters(rows)

    if check_id == "relationship_definitions":
        return _normalize_relationship_definitions(rows)

    raise ValueError(f"Unsupported validation check_id: {check_id}")


def normalize_expected_value(expected_value: Any) -> Any:
    """Normalize expected values for stable comparison."""
    if isinstance(expected_value, list):
        return _sorted_list(expected_value)

    if isinstance(expected_value, dict):
        normalized_dict: dict[str, Any] = {}

        for key, value in expected_value.items():
            if isinstance(value, list):
                normalized_dict[key] = _sorted_list(value)
            elif isinstance(value, dict):
                normalized_dict[key] = dict(sorted(value.items()))
            else:
                normalized_dict[key] = value

        return dict(sorted(normalized_dict.items()))

    return expected_value


def compare_result(
    check_id: str,
    actual_rows: list[dict[str, Any]],
    expected_value: Any,
) -> dict[str, Any]:
    """Compare actual Neo4j query result with expected schema state."""
    actual_normalized = normalize_actual_result(check_id, actual_rows)
    expected_normalized = normalize_expected_value(expected_value)

    passed = actual_normalized == expected_normalized

    return {
        "check_id": check_id,
        "passed": passed,
        "actual": actual_normalized,
        "expected": expected_normalized,
    }