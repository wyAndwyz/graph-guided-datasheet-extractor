# .\.venv\Scripts\Activate.ps1
# $env:PYTHONPATH="src"
# python -m graph_datasheet_extractor.cq_validation.main_generate_cq

from __future__ import annotations

import json

from graph_datasheet_extractor.cq_validation.expected_cq_loader import (
    load_cq_validation_targets,
)
from graph_datasheet_extractor.cq_validation.llm_cq_generator import (
    generate_cq_query_for_target,
)
from graph_datasheet_extractor.schema_validation.schema_validation_runner import (
    get_project_root,
)


def main() -> None:
    project_root = get_project_root()
    targets_path = project_root / "validation_specs" / "cq_validation_targets.yaml"

    targets = load_cq_validation_targets(targets_path)

    first_target = targets[0]
    generated = generate_cq_query_for_target(first_target)

    print(json.dumps(generated.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()