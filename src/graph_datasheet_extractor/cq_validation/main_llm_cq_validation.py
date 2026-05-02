# .\.venv\Scripts\Activate.ps1
# $env:PYTHONPATH="src"
# python -m graph_datasheet_extractor.cq_validation.main_llm_cq_validation

from __future__ import annotations

import json
import sys
from pathlib import Path

from graph_datasheet_extractor.cq_validation.llm_cq_validation_runner import (
    run_llm_cq_validation,
)


def print_report_summary(report: dict) -> None:
    """Print a compact LLM-assisted CQ validation summary to the terminal."""
    summary = report.get("summary", {})

    print("\n=== LLM-assisted CQ Validation Summary ===")
    print(f"Total checks : {summary.get('total_checks')}")
    print(f"Passed checks: {summary.get('passed_checks')}")
    print(f"Failed checks: {summary.get('failed_checks')}")

    if report.get("passed"):
        print("\nResult: PASSED")
    else:
        print("\nResult: FAILED")
        print("\nFailed checks:")

        for check in report.get("checks", []):
            if not check.get("passed"):
                print(f"- {check.get('check_id')}")
                if check.get("error"):
                    print(f"  Error: {check.get('error')}")
                if check.get("generated_cypher_query"):
                    print("  Generated query:")
                    print(f"  {check.get('generated_cypher_query')}")

    print("\nReport file:")
    print("outputs/validation_reports/llm_cq_validation_report.json")

    print("\nGenerated CQ query log:")
    print("outputs/validation_reports/llm_generated_cq_queries.json")


def main() -> int:
    """Run LLM-assisted CQ validation from a dedicated entry point."""
    try:
        report = run_llm_cq_validation()
        print_report_summary(report)

        return 0 if report.get("passed") else 1

    except Exception as exc:
        print("\nLLM-assisted CQ validation failed with an exception:")
        print(str(exc))

        debug_report_path = Path("outputs/validation_reports/llm_cq_validation_error.json")
        debug_report_path.parent.mkdir(parents=True, exist_ok=True)

        debug_report = {
            "validation_type": "llm_assisted_cq_validation",
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