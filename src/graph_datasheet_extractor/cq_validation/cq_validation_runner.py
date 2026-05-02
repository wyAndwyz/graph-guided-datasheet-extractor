from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from graph_datasheet_extractor.cq_validation.cq_result_comparator import (
    compare_cq_result,
)
from graph_datasheet_extractor.cq_validation.expected_cq_loader import (
    load_cq_validation_targets,
    load_expected_cq_results,
)
from graph_datasheet_extractor.schema_validation.safe_cypher_checker import (
    assert_read_only_cypher,
)
from graph_datasheet_extractor.schema_validation.schema_validation_runner import (
    get_neo4j_connection_config,
    get_project_root,
    run_cypher_query,
)


CHECK_TO_CQ_QUERY_FILE = {
    "cq1_extracted_equipment": "cq1_extracted_equipment.cypher",
    "cq2_technical_parameters": "cq2_technical_parameters.cypher",
    "cq3_parameter_evidence": "cq3_parameter_evidence.cypher",
    "cq4_vocabulary_grounding": "cq4_vocabulary_grounding.cypher",
    "cq5_required_parameter_status": "cq5_required_parameter_status.cypher",
}


def load_text_file(path: str | Path) -> str:
    """Load a text file as UTF-8."""
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return file_path.read_text(encoding="utf-8")


def run_cq_validation() -> dict[str, Any]:
    """Run deterministic CQ validation against the populated Neo4j instance graph."""
    project_root = get_project_root()

    expected_results_path = project_root / "validation_specs" / "expected_cq_results.json"
    validation_targets_path = project_root / "validation_specs" / "cq_validation_targets.yaml"
    cq_query_dir = project_root / "graph" / "cq_validation_queries"

    output_dir = project_root / "outputs" / "validation_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "cq_validation_report.json"

    expected_results = load_expected_cq_results(expected_results_path)
    validation_targets = load_cq_validation_targets(validation_targets_path)
    neo4j_config = get_neo4j_connection_config()

    check_results: list[dict[str, Any]] = []

    for target in validation_targets:
        check_id = target["check_id"]
        expected_result_key = target["expected_result_key"]

        if check_id not in CHECK_TO_CQ_QUERY_FILE:
            raise ValueError(f"No CQ query file configured for check_id: {check_id}")

        if expected_result_key not in expected_results:
            raise ValueError(
                f"Expected result key '{expected_result_key}' not found in expected CQ results."
            )

        query_file_name = CHECK_TO_CQ_QUERY_FILE[check_id]
        query_path = cq_query_dir / query_file_name
        query = load_text_file(query_path)

        assert_read_only_cypher(query)

        actual_rows = run_cypher_query(query, neo4j_config)

        comparison = compare_cq_result(
            check_id=check_id,
            actual_rows=actual_rows,
            expected_rows=expected_results[expected_result_key],
        )

        comparison["description"] = target.get("description")
        comparison["query_file"] = str(query_path.relative_to(project_root))

        check_results.append(comparison)

    passed_count = sum(1 for item in check_results if item["passed"])
    failed_count = len(check_results) - passed_count

    report = {
        "validation_type": "deterministic_cq_validation",
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