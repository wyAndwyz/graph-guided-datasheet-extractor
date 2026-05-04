# Pipeline Overview

This document describes the current and planned pipeline of the `graph-guided-datasheet-extractor` project.

The project is developed in phases. The current implemented version focuses on the graph backend MVP. Later phases will extend the workflow step by step from raw PDF datasheets to graph-guided LLM extraction, Neo4j population, validation, and report generation.

## Core Idea

The project explores a graph-guided workflow for extracting technical information from datasheets.

Instead of treating information extraction as a flat key-value extraction task, the project represents extracted information as graph-shaped data:

```text
Datasheet
    → Equipment
        → TechnicalParameter
            → ParameterType
            → Unit
            → Evidence
            → ExtractionRun
```

The knowledge graph is used in two complementary ways:

```text
before extraction:
    guide document screening and extraction targets

after extraction:
    validate, query, and audit extracted information
```

This makes the pipeline more controlled than a direct "PDF to LLM to JSON" workflow.

## Full Planned Pipeline

The planned end-to-end pipeline is:

```text
PDF datasheet
    ↓
local PDF text extraction
    ↓
graph-guided page/content screening
    ↓
selected content blocks
    ↓
LangChain structured extraction
    ↓
graph-shaped JSON
    ↓
Pydantic graph JSON validation
    ↓
Neo4j graph population
    ↓
Cypher-based CQ validation
    ↓
LLM-assisted validation/query generation
    ↓
LangGraph workflow orchestration
    ↓
JSON/HTML report generation
```

The current repository does not implement the full pipeline yet. It implements the backend part first.

## Phase 1 — Graph Backend MVP

Status: **basically complete**.

Phase 1 starts from a manually prepared graph-shaped JSON file and validates the graph backend workflow.

Current Phase 1 pipeline:

```text
Neo4j schema initialization
    ↓
control/vocabulary graph initialization
    ↓
schema/control graph validation
    ↓
manual graph-shaped JSON sample
    ↓
Pydantic graph JSON validation
    ↓
Neo4j graph population
    ↓
deterministic CQ validation
    ↓
LLM-assisted Cypher query generation and validation
```

Implemented components:

```text
Neo4j schema and constraints
control/vocabulary graph
schema validation
LLM-assisted schema validation
graph-shaped JSON format
Pydantic graph JSON models
graph JSON validation
manual gold graph extraction sample
Neo4j graph loading
deterministic CQ validation
LLM-assisted CQ query generation and validation
```

Main input:

```text
data/gold/sample_graph_extraction.json
```

Main outputs:

```text
outputs/validation_reports/schema_validation_report.json
outputs/validation_reports/llm_schema_validation_report.json
outputs/validation_reports/graph_json_validation_report.json
outputs/validation_reports/sample_graph_loading_report.json
outputs/validation_reports/cq_validation_report.json
outputs/validation_reports/llm_cq_validation_report.json
```

Main source folders:

```text
src/graph_datasheet_extractor/schema_validation/
src/graph_datasheet_extractor/graph_representation/
src/graph_datasheet_extractor/graph_population/
src/graph_datasheet_extractor/cq_validation/
```

Relevant documentation:

```text
docs/how_to_run_current_mvp.md
docs/graph_model.md
docs/graph_json_format.md
docs/cq_validation.md
docs/llm_assisted_schema_validation.md
docs/cypher_schema_explanation.md
```

## Phase 2 — Document Screening Pipeline

Status: **planned next implementation phase**.

Phase 2 extends the workflow one step earlier: from raw PDF datasheet to selected content blocks.

Phase 2 pipeline:

```text
PDF datasheet
    ↓
page-level text extraction
    ↓
page scoring
    ↓
page selection
    ↓
content block construction
    ↓
selected_content_blocks.json
```

Planned source folder:

```text
src/graph_datasheet_extractor/preprocessing/
├─ __init__.py
├─ pdf_text_extractor.py
├─ page_scorer.py
├─ page_selector.py
└─ content_block_builder.py
```

Planned entry points:

```text
src/graph_datasheet_extractor/preprocessing/main_extract_page_texts.py
src/graph_datasheet_extractor/preprocessing/main_screen_document.py
```

Planned outputs:

```text
outputs/intermediate/page_texts.json
outputs/intermediate/page_scores.json
outputs/intermediate/selected_content_blocks.json
```

The first implementation should remain local and deterministic. It should not call an LLM.

The main purpose is to reduce token cost and hallucination risk before structured LLM extraction.

Relevant documentation:

```text
docs/document_screening.md
```

## Phase 3 — LangChain Structured Extraction

Status: **planned after document screening**.

Phase 3 will use selected content blocks as controlled input for structured LLM extraction.

Phase 3 pipeline:

```text
selected_content_blocks.json
    ↓
graph schema and vocabulary context
    ↓
LangChain prompt
    ↓
structured output model
    ↓
graph-shaped JSON
```

Planned source folders:

```text
src/graph_datasheet_extractor/langchain_components/
├─ __init__.py
├─ structured_output_models.py
├─ prompt_templates.py
└─ extraction_chain.py

src/graph_datasheet_extractor/extraction/
├─ __init__.py
└─ graph_guided_extractor.py
```

Planned output:

```text
outputs/graph_json/extracted_graph.json
```

This phase will be the first phase where automatic LLM-based information extraction is introduced.

The LLM output should not be directly trusted. It must be validated as graph-shaped JSON before loading into Neo4j.

## Phase 4 — End-to-End Pipeline Runner

Status: **planned after Phase 3**.

Phase 4 will connect the previously separated steps into one executable pipeline.

Planned pipeline:

```text
PDF datasheet
    ↓
document screening
    ↓
LangChain structured extraction
    ↓
graph-shaped JSON validation
    ↓
Neo4j graph population
    ↓
CQ validation
    ↓
report generation
```

Planned source folder:

```text
src/graph_datasheet_extractor/pipeline/
├─ __init__.py
├─ pipeline_steps.py
└─ run_pipeline.py
```

Possible command:

```powershell
python -m graph_datasheet_extractor.pipeline.run_pipeline
```

Planned outputs:

```text
outputs/intermediate/page_texts.json
outputs/intermediate/page_scores.json
outputs/intermediate/selected_content_blocks.json
outputs/graph_json/extracted_graph.json
outputs/validation_reports/pipeline_validation_report.json
outputs/html_reports/pipeline_report.html
```

## Phase 5 — LangGraph Workflow

Status: **planned after the basic end-to-end pipeline is stable**.

LangGraph should not be introduced too early. It becomes useful when the workflow has state, conditional branches, validation failures, retries, repair attempts, and optional human review.

Planned LangGraph workflow:

```text
Document loaded
    ↓
Screen pages
    ↓
Build schema/vocabulary context
    ↓
Extract with LLM
    ↓
Validate graph-shaped JSON
    ↓
If invalid: repair or retry
    ↓
If valid: load into Neo4j
    ↓
Run CQ validation
    ↓
If validation fails: inspect or repair
    ↓
Generate report
```

Planned source folder:

```text
src/graph_datasheet_extractor/langgraph_workflow/
├─ __init__.py
├─ state.py
├─ nodes.py
├─ edges.py
└─ workflow.py
```

The goal of LangGraph is not to make the project look more complex. Its role is to make the pipeline stateful, inspectable, and robust.

## Current vs. Planned Inputs

### Current implemented input

The current MVP uses a manually prepared graph-shaped JSON file:

```text
data/gold/sample_graph_extraction.json
```

This makes the graph backend testable before automatic extraction is implemented.

### Planned future input

The future full pipeline will use raw PDF datasheets:

```text
data/raw/vishay_temt6000x01_datasheet.pdf
data/raw/analog_devices_adxl345_datasheet.pdf
```

The PDFs will first go through document screening. Only selected content blocks will be sent to the LLM.

## Current vs. Planned Outputs

### Current implemented outputs

```text
outputs/validation_reports/
```

Current validation reports include:

```text
schema_validation_report.json
llm_schema_validation_report.json
graph_json_validation_report.json
sample_graph_loading_report.json
cq_validation_report.json
llm_cq_validation_report.json
```

### Planned future outputs

```text
outputs/intermediate/page_texts.json
outputs/intermediate/page_scores.json
outputs/intermediate/selected_content_blocks.json
outputs/extracted_json/
outputs/normalized_json/
outputs/graph_json/
outputs/html_reports/
```

The exact output names may evolve as the implementation becomes more stable.

## Validation Strategy

The pipeline uses validation at multiple points.

Current validation layers:

```text
Neo4j constraints
schema/control graph validation
LLM-assisted schema validation
Pydantic graph JSON validation
Neo4j graph population checks
deterministic CQ validation
LLM-assisted CQ validation
```

Planned future validation layers:

```text
document screening sanity checks
selected content block validation
structured LLM output validation
repair/retry validation
end-to-end pipeline report validation
```

Important rule:

```text
LLM-generated outputs are treated as candidate outputs, not trusted logic.
```

This applies to both generated Cypher queries and future generated extraction JSON.

## Role of Neo4j

Neo4j is used as the graph backend and semantic control layer.

Current roles:

```text
store graph schema/control vocabulary
store allowed relationships
store parameter vocabulary
store unit vocabulary
store equipment type vocabulary
store extracted graph instances
support Cypher validation
support competency-question queries
```

Planned roles:

```text
guide document screening
provide graph schema context for prompts
provide vocabulary constraints for extraction
support validation of extracted information
support graph-based inspection and reporting
```

## Role of LangChain

Current roles:

```text
LLM-assisted schema validation query generation
LLM-assisted CQ query generation
structured output handling for generated Cypher
prompt construction for controlled query generation
```

Planned roles:

```text
structured extraction from selected content blocks
graph-guided prompt construction
Pydantic structured output parsing
repair prompt construction
```

## Role of LangGraph

LangGraph is planned for the later workflow phase.

It should be used when the project needs:

```text
state management
conditional branches
validation-dependent routing
retry limits
repair attempts
optional human review
workflow-level reporting
```

It is intentionally not part of the current Phase 1 MVP.

## Recommended Development Order

The recommended next development order is:

```text
1. Finish Phase 1 documentation.
2. Implement Phase 2 document screening.
3. Add deterministic tests for screening outputs.
4. Implement Phase 3 LangChain structured extraction.
5. Connect the steps through a Phase 4 pipeline runner.
6. Add LangGraph only after the end-to-end pipeline has meaningful branches.
```

Current immediate next step:

```text
Implement:
src/graph_datasheet_extractor/preprocessing/pdf_text_extractor.py

Then add:
src/graph_datasheet_extractor/preprocessing/main_extract_page_texts.py
```

## Design Boundary

This project is not intended to demonstrate that an LLM can read an entire datasheet in one prompt.

The intended design claim is different:

```text
A knowledge graph can provide semantic control before and after LLM-based extraction.
```

This means:

```text
before extraction:
    define target concepts, vocabulary, units, and screening criteria

during extraction:
    constrain the expected structured output

after extraction:
    validate, query, and audit graph-shaped results
```

This boundary is important for keeping the repository credible as an engineering-oriented portfolio demo.
