from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from graph_datasheet_extractor.schema_validation.cypher_result_comparator import (
    compare_result,
)
from graph_datasheet_extractor.schema_validation.expected_state_loader import (
    load_expected_schema_state,
    load_schema_validation_targets,
)
from graph_datasheet_extractor.schema_validation.safe_cypher_checker import (
    assert_read_only_cypher,
)


CHECK_TO_BASELINE_QUERY_FILE = {
    "parameter_type_vocabulary": "check_parameter_type_vocabulary.cypher",
    "unit_vocabulary": "check_unit_vocabulary.cypher",
    "equipment_type_vocabulary": "check_equipment_type_vocabulary.cypher",
    "allowed_units": "check_allowed_units.cypher",
    "required_parameters": "check_required_parameters.cypher",
    "relationship_definitions": "check_relationship_definitions.cypher",
}


def get_project_root() -> Path:
    """Return the repository root based on this file location."""
    return Path(__file__).resolve().parents[3]


def load_text_file(path: str | Path) -> str:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return file_path.read_text(encoding="utf-8")


def get_neo4j_connection_config() -> dict[str, str]:
    """Load Neo4j connection settings from environment variables."""
    if load_dotenv is not None:
        load_dotenv()

    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "password"),
        "database": os.getenv("NEO4J_DATABASE", "neo4j"),
    }


def run_cypher_query(
    query: str,
    neo4j_config: dict[str, str],
) -> list[dict[str, Any]]:
    """Run a read-only Cypher query and return rows as dictionaries."""
    assert_read_only_cypher(query)

    driver = GraphDatabase.driver(
        neo4j_config["uri"],
        auth=(neo4j_config["user"], neo4j_config["password"]),
    )

    try:
        with driver.session(database=neo4j_config["database"]) as session:
            result = session.run(query)
            return [dict(record) for record in result]
    finally:
        driver.close()


def run_schema_validation() -> dict[str, Any]:
    """Run deterministic baseline schema validation against Neo4j."""
    project_root = get_project_root()

    expected_state_path = project_root / "validation_specs" / "expected_schema_state.json"
    validation_targets_path = project_root / "validation_specs" / "schema_validation_targets.yaml"
    baseline_query_dir = project_root / "graph" / "schema_validation_queries"

    output_dir = project_root / "outputs" / "validation_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "schema_validation_report.json"

    expected_state = load_expected_schema_state(expected_state_path)
    validation_targets = load_schema_validation_targets(validation_targets_path)
    neo4j_config = get_neo4j_connection_config()

    check_results: list[dict[str, Any]] = []

    for target in validation_targets:
        check_id = target["check_id"]
        expected_result_key = target["expected_result_key"]

        if check_id not in CHECK_TO_BASELINE_QUERY_FILE:
            raise ValueError(f"No baseline query file configured for check_id: {check_id}")

        if expected_result_key not in expected_state:
            raise ValueError(
                f"Expected result key '{expected_result_key}' not found in expected schema state."
            )

        query_file_name = CHECK_TO_BASELINE_QUERY_FILE[check_id]
        query_path = baseline_query_dir / query_file_name
        query = load_text_file(query_path)

        actual_rows = run_cypher_query(query, neo4j_config)
        comparison = compare_result(
            check_id=check_id,
            actual_rows=actual_rows,
            expected_value=expected_state[expected_result_key],
        )

        comparison["description"] = target.get("description")
        comparison["query_file"] = str(query_path.relative_to(project_root))

        check_results.append(comparison)

    passed_count = sum(1 for item in check_results if item["passed"])
    failed_count = len(check_results) - passed_count

    report = {
        "validation_type": "deterministic_baseline_schema_validation",
        "passed": failed_count == 0,
        "summary": {
            "total_checks": len(check_results),
            "passed_checks": passed_count,
            "failed_checks": failed_count,
        },
        "checks": check_results,
    }

    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return report


def main() -> None:
    report = run_schema_validation()

    print("Schema validation completed.")
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))

    if report["passed"]:
        print("Result: PASSED")
    else:
        print("Result: FAILED")
        print(f"See report: outputs/validation_reports/schema_validation_report.json")


if __name__ == "__main__":
    main()