# Repository Structure

This document describes the current and planned repository structure for the graph-guided datasheet extraction demo.

The repository is being developed in phases. The current MVP implements the Neo4j graph backend, graph-shaped JSON validation, Neo4j population, deterministic validation, and LLM-assisted Cypher query generation. The full PDF-to-LLM extraction and LangGraph workflow orchestration are planned as later phases.

## Design Principles

The repository structure follows these principles:

- Separate Neo4j schema files, human-readable CQ queries, and validation queries.
- Keep raw datasheets separate from generated outputs.
- Treat graph-shaped JSON as an explicit intermediate representation.
- Validate graph-shaped JSON before writing to Neo4j.
- Use Neo4j constraints and Cypher validation to keep the graph auditable.
- Treat LLM-generated Cypher as candidate output, not trusted logic.
- Use LangChain for structured LLM interactions.
- Introduce LangGraph later, when the full stateful extraction workflow requires branching, retries, repair, and optional human review.
- Keep document screening before LLM extraction to reduce token cost and hallucination risk.
- Keep GraphRAG and multimodal extraction as later extensions.

## Current Implementation Status

The following parts are currently implemented:

```text
Neo4j schema and constraints
Neo4j control/vocabulary graph
schema validation
LLM-assisted schema validation query generation
graph-shaped JSON format
Pydantic graph JSON models and validation
manual gold graph extraction sample
Neo4j graph population from graph-shaped JSON
deterministic CQ validation
LLM-assisted CQ query generation and validation
```

The following parts are planned but not yet implemented:

```text
PDF text extraction
graph-guided page/content screening
LangChain structured extraction from selected content blocks
LLM-generated graph-shaped JSON from real datasheet content
LangGraph end-to-end workflow
automatic repair/retry workflow
HTML report generation
GraphRAG extension
multimodal extraction extension
```

## Current Folder Structure

```text
graph-guided-datasheet-extractor/
│
├─ README.md
├─ LICENSE
├─ .gitignore
├─ .env.example
├─ requirements.txt
├─ docker-compose.yml
│
├─ data/
│  ├─ README.md
│  ├─ raw/
│  │  ├─ README.md
│  │  ├─ vishay_temt6000x01_datasheet.pdf
│  │  └─ analog_devices_adxl345_datasheet.pdf
│  │
│  ├─ sample/
│  │  └─ README.md
│  │
│  └─ gold/
│     └─ sample_graph_extraction.json
│
├─ graph/
│  ├─ schema/
│  │  ├─ 01_create_constraints.cypher
│  │  ├─ 02_init_control_graph.cypher
│  │  ├─ 03_equipment_schema.cypher
│  │  ├─ 04_parameter_schema.cypher
│  │  └─ 05_unit_vocabulary.cypher
│  │
│  ├─ queries/
│  │  ├─ cq1_list_extracted_equipment.cypher
│  │  ├─ cq2_list_technical_parameters.cypher
│  │  ├─ cq3_trace_parameter_to_evidence.cypher
│  │  ├─ cq4_check_vocabulary_grounding.cypher
│  │  └─ cq5_required_parameter_status.cypher
│  │
│  ├─ schema_validation_queries/
│  │  ├─ check_parameter_type_vocabulary.cypher
│  │  ├─ check_unit_vocabulary.cypher
│  │  ├─ check_equipment_type_vocabulary.cypher
│  │  ├─ check_allowed_units.cypher
│  │  ├─ check_required_parameters.cypher
│  │  └─ check_relationship_definitions.cypher
│  │
│  ├─ cq_validation_queries/
│  │  ├─ cq1_extracted_equipment.cypher
│  │  ├─ cq2_technical_parameters.cypher
│  │  ├─ cq3_parameter_evidence.cypher
│  │  ├─ cq4_vocabulary_grounding.cypher
│  │  └─ cq5_required_parameter_status.cypher
│  │
│  └─ README.md
│
├─ validation_specs/
│  ├─ expected_schema_state.json
│  ├─ schema_validation_targets.yaml
│  ├─ expected_cq_results.json
│  └─ cq_validation_targets.yaml
│
├─ src/
│  └─ graph_datasheet_extractor/
│     ├─ __init__.py
│     │
│     ├─ schema_validation/
│     │  ├─ __init__.py
│     │  ├─ expected_state_loader.py
│     │  ├─ safe_cypher_checker.py
│     │  ├─ cypher_result_comparator.py
│     │  ├─ schema_validation_runner.py
│     │  ├─ main_validation.py
│     │  ├─ llm_cypher_generator.py
│     │  ├─ main_generate_cypher.py
│     │  ├─ llm_validation_runner.py
│     │  └─ main_llm_validation.py
│     │
│     ├─ graph_representation/
│     │  ├─ __init__.py
│     │  ├─ graph_models.py
│     │  ├─ graph_json_validator.py
│     │  └─ main_validate_graph_json.py
│     │
│     ├─ graph_population/
│     │  ├─ __init__.py
│     │  ├─ graph_loader.py
│     │  └─ main_load_sample_graph.py
│     │
│     └─ cq_validation/
│        ├─ __init__.py
│        ├─ expected_cq_loader.py
│        ├─ cq_result_comparator.py
│        ├─ cq_validation_runner.py
│        ├─ main_cq_validation.py
│        ├─ llm_cq_generator.py
│        ├─ main_generate_cq.py
│        ├─ llm_cq_validation_runner.py
│        └─ main_llm_cq_validation.py
│
├─ outputs/
│  ├─ intermediate/
│  │  └─ .gitkeep
│  │
│  ├─ extracted_json/
│  │  └─ .gitkeep
│  │
│  ├─ normalized_json/
│  │  └─ .gitkeep
│  │
│  ├─ graph_json/
│  │  └─ .gitkeep
│  │
│  ├─ validation_reports/
│  │  ├─ schema_validation_report.json
│  │  ├─ llm_schema_validation_report.json
│  │  ├─ graph_json_validation_report.json
│  │  ├─ sample_graph_loading_report.json
│  │  ├─ cq_validation_report.json
│  │  └─ llm_cq_validation_report.json
│  │
│  └─ html_reports/
│     └─ .gitkeep
│
└─ docs/
   ├─ cq_validation.md
   ├─ cypher_schema_explanation.md
   ├─ datasheet_selection.md
   ├─ graph_json_format.md
   ├─ graph_model.md
   ├─ llm_assisted_schema_validation.md
   └─ repo_structure.md
```

## Directory Responsibilities

### data/

Contains input and reference data.

```text
data/raw/
```

Stores locally downloaded public datasheet PDFs. PDF files may be ignored by Git depending on the repository policy.

```text
data/sample/
```

Reserved for small synthetic or shareable sample inputs.

```text
data/gold/
```

Stores manually prepared reference outputs. The current MVP uses:

```text
sample_graph_extraction.json
```

This file is the manually prepared graph-shaped JSON used to test graph JSON validation and Neo4j population.

### graph/

Contains Neo4j-related Cypher files.

```text
graph/schema/
```

Stores schema and vocabulary initialization scripts:

```text
01_create_constraints.cypher
02_init_control_graph.cypher
03_equipment_schema.cypher
04_parameter_schema.cypher
05_unit_vocabulary.cypher
```

These scripts create constraints, control concepts, relationship definitions, parameter vocabulary, equipment type vocabulary, and unit vocabulary.

```text
graph/queries/
```

Stores human-readable competency-question queries for interactive inspection in Neo4j Browser.

```text
graph/schema_validation_queries/
```

Stores deterministic baseline Cypher queries for validating the control/vocabulary graph.

```text
graph/cq_validation_queries/
```

Stores deterministic baseline Cypher queries for validating the populated instance graph against competency questions.

### validation_specs/

Contains local expected outputs and validation target descriptions.

```text
expected_schema_state.json
```

Defines the expected Neo4j control/vocabulary graph state.

```text
schema_validation_targets.yaml
```

Defines schema validation targets used by deterministic and LLM-assisted schema validation.

```text
expected_cq_results.json
```

Defines expected results for CQ1-CQ5 over the populated sample graph.

```text
cq_validation_targets.yaml
```

Defines CQ validation targets used by deterministic and LLM-assisted CQ validation.

### src/graph_datasheet_extractor/schema_validation/

Contains schema/control-graph validation code.

Key responsibilities:

- load expected schema state;
- load schema validation target definitions;
- check whether generated Cypher is read-only;
- run deterministic baseline schema validation;
- generate schema validation Cypher with LangChain;
- run LLM-assisted schema validation;
- write validation reports.

Main entry points:

```text
main_validation.py
main_generate_cypher.py
main_llm_validation.py
```

### src/graph_datasheet_extractor/graph_representation/

Contains graph-shaped JSON models and validators.

Key responsibilities:

- define Pydantic models for `GraphExtraction`, `GraphNode`, `GraphRelationship`, and `TargetRef`;
- validate graph-shaped JSON structure;
- check local node references;
- check `target` vs. `target_ref` usage;
- check required evidence and technical-parameter relationships.

Main entry point:

```text
main_validate_graph_json.py
```

### src/graph_datasheet_extractor/graph_population/

Contains Neo4j graph loading code.

Key responsibilities:

- load validated graph-shaped JSON into Neo4j;
- create or update instance nodes;
- create relationships to local JSON nodes through `target`;
- create relationships to existing vocabulary nodes through `target_ref`;
- keep control/vocabulary graph nodes separate from extracted instance nodes.

Main entry point:

```text
main_load_sample_graph.py
```

### src/graph_datasheet_extractor/cq_validation/

Contains deterministic and LLM-assisted competency-question validation code.

Key responsibilities:

- load expected CQ results;
- load CQ validation targets;
- run hand-written CQ Cypher queries;
- compare actual results with expected CQ results;
- generate CQ Cypher queries with LangChain;
- run LLM-assisted CQ validation;
- write CQ validation reports.

Main entry points:

```text
main_cq_validation.py
main_generate_cq.py
main_llm_cq_validation.py
```

### outputs/

Contains generated intermediate and final outputs.

Current MVP outputs are mainly stored in:

```text
outputs/validation_reports/
```

Typical report files:

```text
schema_validation_report.json
llm_schema_validation_report.json
graph_json_validation_report.json
graph_json_validation_before_loading_report.json
sample_graph_loading_report.json
cq_validation_report.json
llm_cq_validation_report.json
llm_generated_cypher_queries.json
llm_generated_cq_queries.json
```

Generated outputs should generally be ignored by Git unless a specific report is intentionally kept as a demo artifact.

### docs/

Contains project documentation.

Current documents:

```text
cq_validation.md
cypher_schema_explanation.md
datasheet_selection.md
graph_json_format.md
graph_model.md
llm_assisted_schema_validation.md
repo_structure.md
```

Recommended next documents:

```text
pipeline.md
document_screening.md
demo_walkthrough.md
```

## Planned Extensions

The following folders are planned for later phases.

### configs/

Planned configuration folder:

```text
configs/
├─ pipeline_config.yaml
├─ llm_config.yaml
├─ langchain_config.yaml
├─ langgraph_config.yaml
├─ neo4j_config.yaml
├─ extraction_targets.yaml
└─ validation_config.yaml
```

No secrets should be stored here. API keys and passwords should remain in `.env`.

### prompts/

Planned prompt-template folder:

```text
prompts/
├─ system_prompt.md
├─ graph_guided_extraction_prompt.md
├─ evidence_grounding_prompt.md
├─ normalization_prompt.md
├─ repair_prompt.md
└─ README.md
```

Prompt files should not contain hard-coded datasheet-specific values. Dynamic context such as graph schema, target parameters, allowed units, and selected content blocks should be injected at runtime.

### preprocessing/

Planned module:

```text
src/graph_datasheet_extractor/preprocessing/
├─ pdf_text_extractor.py
├─ page_scorer.py
├─ page_selector.py
└─ content_block_builder.py
```

This module will implement local text extraction and graph-guided page/content screening before LLM calls.

### langchain_components/

Planned module:

```text
src/graph_datasheet_extractor/langchain_components/
├─ structured_output_models.py
├─ prompt_templates.py
└─ extraction_chain.py
```

This module will implement LangChain prompt construction and structured extraction from selected content blocks.

### langgraph_workflow/

Planned module:

```text
src/graph_datasheet_extractor/langgraph_workflow/
├─ state.py
├─ nodes.py
├─ edges.py
└─ workflow.py
```

This module will orchestrate the full pipeline once document screening and LLM extraction are implemented.

### pipeline/

Planned module:

```text
src/graph_datasheet_extractor/pipeline/
├─ run_pipeline.py
└─ pipeline_steps.py
```

This module will provide the end-to-end pipeline runner.

### reporting/

Planned module:

```text
src/graph_datasheet_extractor/reporting/
├─ json_report_builder.py
└─ html_report_builder.py
```

This module will generate final JSON and HTML reports.

### tests/

Planned test folder:

```text
tests/
├─ test_graph_json_validator.py
├─ test_graph_population.py
├─ test_schema_validation.py
├─ test_cq_validation.py
└─ fixtures/
```

## Notes on Current vs. Planned Structure

Earlier project notes included a larger final repository structure with folders such as `configs/`, `prompts/`, `pipeline/`, `preprocessing/`, `langchain_components/`, `langgraph_workflow/`, `reporting/`, and `tests/`.

Those folders are still part of the planned roadmap, but the current MVP intentionally focuses on the graph backend first:

```text
graph-shaped JSON
    ↓
validation
    ↓
Neo4j population
    ↓
CQ validation
    ↓
LLM-assisted Cypher generation
```

This keeps the first runnable version small, auditable, and testable before adding automatic PDF processing and full LLM extraction.
