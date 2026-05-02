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
from graph_datasheet_extractor.cq_validation.llm_cq_generator import (
    GeneratedCqQuery,
    generate_cq_query_for_target,
)
from graph_datasheet_extractor.schema_validation.safe_cypher_checker import (
    assert_read_only_cypher,
)
from graph_datasheet_extractor.schema_validation.schema_validation_runner import (
    get_neo4j_connection_config,
    get_project_root,
    run_cypher_query,
)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON data to disk with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def validate_generated_cq_query(
    target: dict[str, Any],
    generated_query: GeneratedCqQuery,
    expected_results: dict[str, Any],
    neo4j_config: dict[str, str],
) -> dict[str, Any]:
    """Run one LLM-generated CQ query and compare the result with expected CQ output."""
    check_id = target["check_id"]
    expected_result_key = target["expected_result_key"]

    if generated_query.check_id != check_id:
        raise ValueError(
            f"Generated check_id does not match target check_id. "
            f"Expected '{check_id}', got '{generated_query.check_id}'."
        )

    if expected_result_key not in expected_results:
        raise ValueError(
            f"Expected result key '{expected_result_key}' not found in expected CQ results."
        )

    cypher_query = generated_query.cypher_query.strip()

    assert_read_only_cypher(cypher_query)

    actual_rows = run_cypher_query(cypher_query, neo4j_config)

    comparison = compare_cq_result(
        check_id=check_id,
        actual_rows=actual_rows,
        expected_rows=expected_results[expected_result_key],
    )

    comparison["description"] = target.get("description")
    comparison["expected_result_key"] = expected_result_key
    comparison["generated_cypher_query"] = cypher_query
    comparison["llm_explanation"] = generated_query.explanation
    comparison["query_source"] = "llm_generated"

    return comparison


def run_llm_cq_validation() -> dict[str, Any]:
    """Run LLM-assisted CQ validation against the populated Neo4j graph."""
    project_root = get_project_root()

    expected_results_path = project_root / "validation_specs" / "expected_cq_results.json"
    validation_targets_path = project_root / "validation_specs" / "cq_validation_targets.yaml"

    output_dir = project_root / "outputs" / "validation_reports"
    output_path = output_dir / "llm_cq_validation_report.json"
    generated_queries_path = output_dir / "llm_generated_cq_queries.json"

    expected_results = load_expected_cq_results(expected_results_path)
    validation_targets = load_cq_validation_targets(validation_targets_path)
    neo4j_config = get_neo4j_connection_config()

    check_results: list[dict[str, Any]] = []
    generated_queries_log: list[dict[str, Any]] = []

    for target in validation_targets:
        check_id = target["check_id"]

        try:
            generated_query = generate_cq_query_for_target(target)

            generated_queries_log.append(
                {
                    "check_id": check_id,
                    "cypher_query": generated_query.cypher_query,
                    "explanation": generated_query.explanation,
                }
            )

            comparison = validate_generated_cq_query(
                target=target,
                generated_query=generated_query,
                expected_results=expected_results,
                neo4j_config=neo4j_config,
            )

            check_results.append(comparison)

        except Exception as exc:
            check_results.append(
                {
                    "check_id": check_id,
                    "passed": False,
                    "description": target.get("description"),
                    "expected_result_key": target.get("expected_result_key"),
                    "query_source": "llm_generated",
                    "error": str(exc),
                }
            )

    passed_count = sum(1 for item in check_results if item.get("passed") is True)
    failed_count = len(check_results) - passed_count

    report = {
        "validation_type": "llm_assisted_cq_validation",
        "passed": failed_count == 0,
        "summary": {
            "total_checks": len(check_results),
            "passed_checks": passed_count,
            "failed_checks": failed_count,
        },
        "checks": check_results,
    }

    _write_json(output_path, report)
    _write_json(
        generated_queries_path,
        {
            "generated_queries": generated_queries_log,
        },
    )

    return report