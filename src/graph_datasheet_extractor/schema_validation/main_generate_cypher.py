# .\.venv\Scripts\Activate.ps1
# $env:PYTHONPATH="src"
# python -m graph_datasheet_extractor.schema_validation.main_validation

from __future__ import annotations

import json

from graph_datasheet_extractor.schema_validation.expected_state_loader import (
    load_schema_validation_targets,
)
from graph_datasheet_extractor.schema_validation.llm_cypher_generator import (
    generate_cypher_for_target,
)
from graph_datasheet_extractor.schema_validation.schema_validation_runner import (
    get_project_root,
)


def main() -> None:
    project_root = get_project_root()
    targets_path = project_root / "validation_specs" / "schema_validation_targets.yaml"

    targets = load_schema_validation_targets(targets_path)

    first_target = targets[0]
    generated = generate_cypher_for_target(first_target)

    print(json.dumps(generated.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()