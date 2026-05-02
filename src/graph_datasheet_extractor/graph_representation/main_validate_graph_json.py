from __future__ import annotations

import json
import sys
from pathlib import Path

from graph_datasheet_extractor.graph_representation.graph_json_validator import (
    validate_graph_extraction_file,
    write_validation_report,
)


def get_project_root() -> Path:
    """Return the repository root based on this file location.

    Current file:
    src/graph_datasheet_extractor/graph_representation/main_validate_graph_json.py

    parents[3] should point to the repository root:
    graph-guided-datasheet-extractor/
    """
    return Path(__file__).resolve().parents[3]


def print_report_summary(report: dict) -> None:
    """Print a compact validation summary to the terminal."""
    summary = report.get("summary", {})

    print("\n=== Graph-shaped JSON Validation Summary ===")
    print(f"Node count                 : {summary.get('node_count')}")
    print(f"Relationship count         : {summary.get('relationship_count')}")
    print(f"TechnicalParameter count   : {summary.get('technical_parameter_count')}")
    print(f"Evidence count             : {summary.get('evidence_count')}")
    print(f"Error count                : {summary.get('error_count')}")

    if report.get("passed"):
        print("\nResult: PASSED")
    else:
        print("\nResult: FAILED")
        print("\nErrors:")

        for error in report.get("errors", []):
            print(f"- {error}")

    print("\nReport file:")
    print("outputs/validation_reports/graph_json_validation_report.json")


def main() -> int:
    """Validate the manual gold graph-shaped JSON sample."""
    project_root = get_project_root()

    input_path = project_root / "data" / "gold" / "sample_graph_extraction.json"
    output_path = (
        project_root
        / "outputs"
        / "validation_reports"
        / "graph_json_validation_report.json"
    )

    try:
        report = validate_graph_extraction_file(input_path)
        write_validation_report(report, output_path)
        print_report_summary(report)

        return 0 if report.get("passed") else 1

    except Exception as exc:
        print("\nGraph-shaped JSON validation failed with an exception:")
        print(str(exc))

        debug_report_path = (
            project_root
            / "outputs"
            / "validation_reports"
            / "graph_json_validation_error.json"
        )
        debug_report_path.parent.mkdir(parents=True, exist_ok=True)

        debug_report = {
            "validation_type": "graph_shaped_json_validation",
            "passed": False,
            "error": str(exc),
        }

        debug_report_path.write_text(
            json.dumps(debug_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print("\nError report file:")
        print(debug_report_path)

        return 1


if __name__ == "__main__":
    sys.exit(main())