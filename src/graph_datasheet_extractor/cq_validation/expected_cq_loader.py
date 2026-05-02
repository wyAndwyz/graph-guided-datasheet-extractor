from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_expected_cq_results(path: str | Path) -> dict[str, Any]:
    """Load expected CQ validation results from JSON."""
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Expected CQ results file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Expected CQ results must be a JSON object.")

    return data


def load_cq_validation_targets(path: str | Path) -> list[dict[str, Any]]:
    """Load CQ validation target definitions from YAML."""
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"CQ validation target file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError("CQ validation target YAML must contain a mapping object.")

    checks = data.get("checks")

    if not isinstance(checks, list):
        raise ValueError("CQ validation target YAML must contain a 'checks' list.")

    for check in checks:
        if "check_id" not in check:
            raise ValueError(f"CQ validation check is missing 'check_id': {check}")
        if "expected_result_key" not in check:
            raise ValueError(
                f"CQ validation check is missing 'expected_result_key': {check}"
            )

    return checks