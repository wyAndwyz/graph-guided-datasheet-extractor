# How to Run the Current Graph Backend MVP

This guide explains how to run the current MVP of the `graph-guided-datasheet-extractor` repository.

The current MVP starts from a manually prepared graph-shaped JSON file and validates the graph backend workflow. It does **not yet** perform PDF text extraction, document screening, automatic LLM extraction from datasheet content, LangGraph orchestration, or report generation.

## 1. What This MVP Demonstrates

The current MVP demonstrates the graph backend and validation part of the project:

```text
Neo4j schema initialization
    ↓
control/vocabulary graph setup
    ↓
schema validation
    ↓
manual graph-shaped JSON sample
    ↓
Pydantic graph JSON validation
    ↓
Neo4j instance graph loading
    ↓
deterministic competency-question validation
    ↓
LLM-assisted Cypher generation and validation
```

The current gold input is:

```text
data/gold/sample_graph_extraction.json
```

This file represents a manually prepared graph-shaped extraction result for the Vishay TEMT6000X01 ambient light sensor datasheet.

## 2. Prerequisites

You need:

- Python 3.10 or later;
- Docker Desktop;
- a local Neo4j instance started through Docker Compose;
- an OpenAI API key if you want to run the LLM-assisted validation steps.

The deterministic parts of the MVP can be run without an OpenAI API key. The LLM-assisted schema validation and LLM-assisted CQ validation require the API key.

## 3. Start Neo4j

From the repository root, start Neo4j with Docker Compose:

```powershell
docker compose up -d
```

Open Neo4j Browser in your web browser:

```text
http://localhost:7474
```

Default local credentials used by the repository:

```text
username: neo4j
password: password
```

## 4. Create and Activate the Python Environment

Create a virtual environment if you have not already done so:

```powershell
python -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Minimum packages used by the current MVP include:

```text
neo4j
pyyaml
python-dotenv
pydantic
langchain
langchain-openai
```

## 5. Configure Environment Variables

Create a local `.env` file in the repository root.

Example:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4o-mini
```

Do not commit `.env` to Git.

If you only run the deterministic validation steps, the OpenAI-related variables are not required.

## 6. Set the Python Path

In PowerShell, run:

```powershell
$env:PYTHONPATH="src"
```

This allows Python to find the `graph_datasheet_extractor` package under `src/`.

## 7. Initialize the Neo4j Schema and Control Graph

Run the Cypher files in the following order.

You can execute them in Neo4j Browser or with `cypher-shell`.

```text
graph/schema/01_create_constraints.cypher
graph/schema/02_init_control_graph.cypher
graph/schema/03_equipment_schema.cypher
graph/schema/04_parameter_schema.cypher
graph/schema/05_unit_vocabulary.cypher
```

These files create:

- Neo4j constraints;
- control graph concepts;
- allowed relationship definitions;
- equipment type vocabulary;
- parameter type vocabulary;
- unit vocabulary;
- required-parameter expectations.

## 8. Run Deterministic Schema Validation

Run:

```powershell
python -m graph_datasheet_extractor.schema_validation.main_validation
```

Expected result:

```text
Result: PASSED
```

This step checks whether the Neo4j schema/control graph matches the expected local schema state.

Typical report output:

```text
outputs/validation_reports/schema_validation_report.json
```

## 9. Run LLM-assisted Schema Validation

Run:

```powershell
python -m graph_datasheet_extractor.schema_validation.main_llm_validation
```

Expected result:

```text
Result: PASSED
```

This step asks the LLM to generate Cypher queries for schema validation targets. The generated Cypher is treated only as candidate output.

The system then:

1. checks whether the generated query is read-only;
2. executes it against Neo4j;
3. compares the result with the expected local output.

Typical report output:

```text
outputs/validation_reports/llm_schema_validation_report.json
```

Generated query output may also be written to:

```text
outputs/validation_reports/llm_generated_cypher_queries.json
```

## 10. Validate the Graph-shaped JSON Sample

Run:

```powershell
python -m graph_datasheet_extractor.graph_representation.main_validate_graph_json
```

Expected result:

```text
Result: PASSED
```

This validates:

- the overall graph-shaped JSON structure;
- local node references;
- relationship target rules;
- correct use of `target` and `target_ref`;
- required links between equipment, parameters, evidence, vocabulary concepts, and extraction runs.

Input file:

```text
data/gold/sample_graph_extraction.json
```

Typical report output:

```text
outputs/validation_reports/graph_json_validation_report.json
```

## 11. Load the Sample Graph into Neo4j

Run:

```powershell
python -m graph_datasheet_extractor.graph_population.main_load_sample_graph
```

Expected result:

```text
Result: PASSED
```

This step loads the validated graph-shaped JSON into Neo4j.

The loader:

- creates or updates extracted instance nodes;
- creates relationships between local extracted nodes;
- connects extracted nodes to existing vocabulary nodes through `target_ref`;
- keeps extracted instance nodes separate from the control/vocabulary graph.

Typical report output:

```text
outputs/validation_reports/sample_graph_loading_report.json
```

## 12. Run Deterministic CQ Validation

Run:

```powershell
python -m graph_datasheet_extractor.cq_validation.main_cq_validation
```

Expected result:

```text
Result: PASSED
```

This step validates the populated sample graph against the five current competency questions.

The current CQs are:

```text
CQ1: Which equipment was extracted from the datasheet?
CQ2: Which technical parameters were extracted for each equipment?
CQ3: Which source evidence supports each extracted parameter?
CQ4: Which extracted parameters are normalized to known graph vocabulary concepts?
CQ5: Which required parameters are missing or use unsupported units?
```

Typical report output:

```text
outputs/validation_reports/cq_validation_report.json
```

## 13. Run LLM-assisted CQ Validation

Run:

```powershell
python -m graph_datasheet_extractor.cq_validation.main_llm_cq_validation
```

Expected current behavior:

```text
CQ1-CQ4: should pass if the generated Cypher matches the expected validation logic
CQ5: may fail because it requires more complex validation-style query logic
```

This is intentional and useful for the demo.

The LLM-generated Cypher is not trusted directly. It is checked by the local validation framework before being accepted.

This shows an important design principle of the project:

```text
LLM-generated queries are candidate outputs, not trusted validation logic.
```

Typical report output:

```text
outputs/validation_reports/llm_cq_validation_report.json
```

Generated query output may also be written to:

```text
outputs/validation_reports/llm_generated_cq_queries.json
```

## 14. Recommended Full Run Order

For a clean run of the current MVP, use this order:

```powershell
# 1. Start Neo4j
docker compose up -d

# 2. Activate environment
.\.venv\Scripts\Activate.ps1

# 3. Set Python path
$env:PYTHONPATH="src"

# 4. Run deterministic schema validation
python -m graph_datasheet_extractor.schema_validation.main_validation

# 5. Run LLM-assisted schema validation
python -m graph_datasheet_extractor.schema_validation.main_llm_validation

# 6. Validate graph-shaped JSON
python -m graph_datasheet_extractor.graph_representation.main_validate_graph_json

# 7. Load sample graph into Neo4j
python -m graph_datasheet_extractor.graph_population.main_load_sample_graph

# 8. Run deterministic CQ validation
python -m graph_datasheet_extractor.cq_validation.main_cq_validation

# 9. Run LLM-assisted CQ validation
python -m graph_datasheet_extractor.cq_validation.main_llm_cq_validation
```

Before step 4, make sure that the schema Cypher files have been executed in Neo4j.

## 15. How to Inspect the Graph Manually

You can inspect the loaded graph in Neo4j Browser.

### List extracted equipment

```cypher
MATCH (d:Datasheet)-[:DESCRIBES]->(e:Equipment)
OPTIONAL MATCH (e)-[:HAS_EQUIPMENT_TYPE]->(et:EquipmentType)
RETURN
  d.id AS datasheet_id,
  d.file_name AS file_name,
  e.id AS equipment_id,
  e.product_model AS product_model,
  et.name AS normalized_equipment_type;
```

### List extracted parameters

```cypher
MATCH (e:Equipment)-[:HAS_PARAMETER]->(p:TechnicalParameter)
MATCH (p)-[:HAS_PARAMETER_TYPE]->(pt:ParameterType)
OPTIONAL MATCH (p)-[:HAS_UNIT]->(u:Unit)
RETURN
  e.product_model AS product_model,
  p.raw_label AS raw_label,
  p.value AS value,
  pt.name AS parameter_type,
  u.symbol AS unit
ORDER BY parameter_type;
```

### Trace parameters to evidence

```cypher
MATCH (p:TechnicalParameter)-[:EVIDENCED_BY]->(ev:Evidence)
RETURN
  p.raw_label AS raw_label,
  p.value AS value,
  ev.page_number AS page_number,
  ev.source_text AS source_text,
  ev.confidence AS confidence
ORDER BY raw_label;
```

### Check vocabulary grounding

```cypher
MATCH (p:TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(pt:ParameterType)
OPTIONAL MATCH (p)-[:HAS_UNIT]->(u:Unit)
RETURN
  p.raw_label AS raw_label,
  pt.name AS parameter_type,
  u.symbol AS unit
ORDER BY pt.name;
```

## 16. Common Problems and Fixes

### Problem: Python cannot find `graph_datasheet_extractor`

Typical error:

```text
ModuleNotFoundError: No module named 'graph_datasheet_extractor'
```

Fix:

```powershell
$env:PYTHONPATH="src"
```

Run the command from the repository root.

### Problem: Neo4j connection fails

Check whether Neo4j is running:

```powershell
docker compose ps
```

Restart Neo4j if needed:

```powershell
docker compose down
docker compose up -d
```

Also check the `.env` values:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j
```

### Problem: Schema validation fails

Possible causes:

- the Cypher schema files were not executed;
- the files were executed in the wrong order;
- the Neo4j database already contains old data from an earlier run;
- the expected schema state was changed but the graph was not reinitialized.

Suggested fix:

1. clear or reset the local Neo4j database if needed;
2. rerun the schema files in order;
3. rerun deterministic schema validation.

### Problem: LLM-assisted validation fails but deterministic validation passes

This can happen because the LLM-generated Cypher does not exactly match the required validation semantics.

This does not necessarily mean the graph is wrong.

The deterministic validation is the baseline. The LLM-assisted validation is used to test whether an LLM can generate acceptable read-only Cypher for a given validation target.

### Problem: CQ5 fails in LLM-assisted validation

CQ5 is more complex than CQ1-CQ4 because it behaves like a validation query rather than a simple retrieval query.

It checks for cases such as:

- missing required parameters;
- unsupported units;
- missing expected units.

Therefore, CQ5 is a useful stress test for LLM-generated Cypher. A failure here shows why LLM-generated validation logic must be checked against deterministic expected outputs.

## 17. What Is Not Covered by This MVP

The following features are planned but not yet implemented:

```text
PDF text extraction
page-level text extraction
page scoring
page/content selection
selected content block construction
LangChain structured extraction from datasheet text
automatic graph-shaped JSON generation
repair prompts
LangGraph workflow orchestration
HTML report generation
GraphRAG extension
multimodal extraction extension
```

These are planned for later phases.

The next implementation phase is document screening:

```text
PDF datasheet
    ↓
page-level text extraction
    ↓
graph-guided page scoring
    ↓
selected content blocks
```

Planned files:

```text
src/graph_datasheet_extractor/preprocessing/pdf_text_extractor.py
src/graph_datasheet_extractor/preprocessing/page_scorer.py
src/graph_datasheet_extractor/preprocessing/page_selector.py
src/graph_datasheet_extractor/preprocessing/content_block_builder.py
```

Planned outputs:

```text
outputs/intermediate/page_texts.json
outputs/intermediate/page_scores.json
outputs/intermediate/selected_content_blocks.json
```

## 18. Recommended Next Step

After this MVP is running successfully, the next recommended step is:

```text
Phase 2 — Document Screening Pipeline
```

This should be implemented before automatic LLM extraction.

Reason:

```text
The knowledge graph should guide not only post-extraction validation,
but also pre-extraction content selection.
```

This reduces token cost, narrows the extraction context, and lowers hallucination risk before calling an LLM.
