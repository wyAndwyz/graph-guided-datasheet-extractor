# .\.venv\Scripts\Activate.ps1
# $env:PYTHONPATH="src"
# python -m graph_datasheet_extractor.graph_population.main_load_sample_graph

from __future__ import annotations

import json
import sys
from pathlib import Path

from graph_datasheet_extractor.graph_population.graph_loader import (
    inspect_loaded_sample_graph,
    load_graph_extraction_to_neo4j,
)
from graph_datasheet_extractor.graph_representation.graph_json_validator import (
    load_graph_extraction_json,
    validate_graph_extraction,
    write_validation_report,
)


def get_project_root() -> Path:
    """Return the repository root based on this file location.

    Current file:
    src/graph_datasheet_extractor/graph_population/main_load_sample_graph.py

    parents[3] should point to:
    graph-guided-datasheet-extractor/
    """
    return Path(__file__).resolve().parents[3]


def print_load_summary(load_summary: dict, inspection_summary: dict) -> None:
    """Print a compact loading summary."""
    print("\n=== Sample Graph Loading Summary ===")
    print(f"Document ID                 : {load_summary.get('document_id')}")
    print(f"Loaded JSON nodes           : {load_summary.get('node_count')}")
    print(f"Loaded JSON relationships   : {load_summary.get('relationship_count')}")
    print(
        "Cleared existing instances  : "
        f"{load_summary.get('cleared_existing_instance_data')}"
    )

    print("\nInstance node counts:")
    for row in inspection_summary.get("instance_node_counts", []):
        print(f"- {row.get('labels')}: {row.get('count')}")

    print("\nRelevant relationship counts:")
    for row in inspection_summary.get("relevant_relationship_counts", []):
        print(f"- {row.get('relationship_type')}: {row.get('count')}")


def main() -> int:
    """Validate and load the manual gold graph-shaped JSON sample into Neo4j."""
    project_root = get_project_root()

    input_path = project_root / "data" / "gold" / "sample_graph_extraction.json"
    validation_report_path = (
        project_root
        / "outputs"
        / "validation_reports"
        / "graph_json_validation_before_loading_report.json"
    )
    load_report_path = (
        project_root
        / "outputs"
        / "validation_reports"
        / "sample_graph_loading_report.json"
    )

    try:
        extraction = load_graph_extraction_json(input_path)

        validation_report = validate_graph_extraction(extraction)
        write_validation_report(validation_report, validation_report_path)

        if not validation_report.get("passed"):
            print("\nGraph-shaped JSON validation failed. Loading aborted.")
            print(f"Validation report: {validation_report_path}")
            return 1

        load_summary = load_graph_extraction_to_neo4j(
            extraction=extraction,
            clear_existing_instance_data=True,
        )

        inspection_summary = inspect_loaded_sample_graph()

        load_report = {
            "loading_type": "manual_gold_sample_graph_loading",
            "passed": True,
            "load_summary": load_summary,
            "inspection_summary": inspection_summary,
        }

        load_report_path.parent.mkdir(parents=True, exist_ok=True)
        load_report_path.write_text(
            json.dumps(load_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print_load_summary(load_summary, inspection_summary)

        print("\nResult: PASSED")
        print("\nReport file:")
        print("outputs/validation_reports/sample_graph_loading_report.json")

        return 0

    except Exception as exc:
        print("\nSample graph loading failed with an exception:")
        print(str(exc))

        error_report = {
            "loading_type": "manual_gold_sample_graph_loading",
            "passed": False,
            "error": str(exc),
        }

        load_report_path.parent.mkdir(parents=True, exist_ok=True)
        load_report_path.write_text(
            json.dumps(error_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print("\nError report file:")
        print("outputs/validation_reports/sample_graph_loading_report.json")

        return 1


if __name__ == "__main__":
    sys.exit(main())