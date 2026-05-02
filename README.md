# Graph-guided Datasheet Extractor

A portfolio demo for graph-guided technical information extraction from public datasheets.

The project explores how a Neo4j knowledge graph can be used not only as a final storage backend, but also as a semantic control layer for LLM-based extraction. The current MVP focuses on the graph backend, graph-shaped JSON validation, Neo4j population, and CQ-based validation. The full PDF-to-LLM extraction pipeline is planned as the next implementation phase.

## Overview

This repository demonstrates a controlled workflow for extracting structured technical information from public electronic and sensor datasheets.

The core idea is:

```text
technical datasheet
    ↓
graph-guided extraction target definition
    ↓
graph-shaped JSON
    ↓
Pydantic validation
    ↓
Neo4j population
    ↓
Cypher-based validation and competency questions
```

Unlike a flat key-value extraction demo, this project represents extracted information as graph elements:

```text
Datasheet
  → Equipment
      → TechnicalParameter
          → ParameterType
          → Unit
          → Evidence
          → ExtractionRun
```

This makes the extraction output auditable, vocabulary-grounded, and queryable.

## Current MVP Status

The current implemented MVP covers the **graph backend and validation pipeline**.

Implemented:

- local Neo4j setup with Docker;
- Neo4j constraints for core node identifiers;
- lightweight control/vocabulary graph;
- `ParameterType`, `Unit`, and `EquipmentType` vocabulary;
- deterministic schema validation against expected schema state;
- LangChain-based LLM-assisted schema validation query generation;
- graph-shaped JSON format;
- Pydantic models for graph-shaped JSON;
- graph-shaped JSON validation;
- manually prepared gold sample extraction JSON;
- Neo4j graph population from graph-shaped JSON;
- deterministic competency-question validation;
- LangChain-based LLM-assisted CQ query generation and validation.

Not yet implemented:

- PDF text extraction;
- graph-guided page/content screening;
- LangChain structured extraction from selected datasheet content;
- LLM-generated graph-shaped JSON from datasheet content;
- LangGraph end-to-end workflow orchestration;
- automatic repair/retry workflow;
- HTML report generation.

## Current Implemented Pipeline

The currently runnable pipeline starts from a manually prepared graph-shaped JSON file:

```text
Neo4j schema initialization
    ↓
schema/control graph validation
    ↓
manual graph-shaped JSON sample
    ↓
Pydantic graph JSON validation
    ↓
Neo4j instance graph population
    ↓
competency-question validation
    ↓
LLM-assisted Cypher query generation and validation
```

The current gold sample is:

```text
data/gold/sample_graph_extraction.json
```

It represents a manually prepared extraction result for the Vishay TEMT6000X01 ambient light sensor datasheet.

## Planned Full Pipeline

The planned full pipeline will extend the current backend MVP to automatic datasheet extraction:

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
graph JSON validation
    ↓
Neo4j graph population
    ↓
CQ validation
    ↓
LangGraph workflow orchestration
    ↓
report generation
```

LangGraph is planned for the stateful workflow phase, where validation branches, repair attempts, retry limits, and optional human review become useful.

## Why Neo4j?

Neo4j is used as a semantic control and validation layer.

In the current MVP, it stores:

- graph schema concepts;
- allowed relationship definitions;
- parameter vocabulary;
- unit vocabulary;
- equipment type vocabulary;
- required-parameter expectations;
- extracted datasheet instances;
- evidence links;
- extraction run information.

The knowledge graph supports:

- vocabulary grounding;
- explicit source evidence tracking;
- Cypher-based validation;
- query-driven graph inspection;
- later graph-guided prompt construction.

## Why Graph-shaped JSON?

The intermediate extraction format is not a flat JSON object. Instead, it is a graph-shaped JSON structure with explicit nodes and relationships.

Example relationship with a local target:

```json
{
  "source": "equipment_vishay_temt6000x01",
  "type": "HAS_PARAMETER",
  "target": "param_dimensions_001"
}
```

Example relationship to an existing vocabulary node:

```json
{
  "source": "param_dimensions_001",
  "type": "HAS_PARAMETER_TYPE",
  "target_ref": {
    "label": "ParameterType",
    "key": "name",
    "value": "Dimensions"
  }
}
```

This design separates extracted instance nodes from existing control/vocabulary graph nodes and prevents duplicate vocabulary nodes from being created during extraction.

See:

```text
docs/graph_json_format.md
```

## Validation Layers

The project uses multiple validation layers:

1. Neo4j constraints
2. deterministic schema validation
3. LLM-assisted schema validation
4. graph-shaped JSON validation
5. Neo4j population validation
6. deterministic CQ validation
7. LLM-assisted CQ validation

LLM-generated queries are treated as candidate queries only. They are checked for read-only safety, executed against Neo4j, and compared against local expected outputs.

## Competency Questions

The current MVP validates five competency questions:

```text
CQ1: Which equipment was extracted from the datasheet?
CQ2: Which technical parameters were extracted for each equipment?
CQ3: Which source evidence supports each extracted parameter?
CQ4: Which extracted parameters are normalized to known graph vocabulary concepts?
CQ5: Which required parameters are missing or use unsupported units?
```

CQ5 currently functions as a validation-style query. It checks missing required parameters, unsupported units, and missing expected units.

## Datasheet Scope

The current demo uses public electronic and sensor-device datasheets.

Primary MVP datasheet:

```text
Vishay TEMT6000X01 ambient light sensor
```

Variation candidate:

```text
Analog Devices ADXL345 3-axis digital accelerometer
```

This scope was selected to keep the portfolio example independent from research-specific or project-specific datasets while still using technically structured documents.

See:

```text
docs/datasheet_selection.md
```

## Repository Structure

The full repository structure is documented in:

```text
docs/repo_structure.md
```

Key folders:

```text
graph/
  schema/                    Neo4j schema and vocabulary initialization Cypher
  queries/                   human-readable CQ queries
  cq_validation_queries/     CQ queries used for automated validation
  schema_validation_queries/ schema validation queries

validation_specs/
  expected_schema_state.json
  schema_validation_targets.yaml
  expected_cq_results.json
  cq_validation_targets.yaml

data/
  raw/                       local datasheet PDFs
  gold/                      manual gold extraction samples

src/graph_datasheet_extractor/
  schema_validation/         schema validation and LLM-assisted schema query generation
  graph_representation/      Pydantic graph-shaped JSON models and validators
  graph_population/          Neo4j graph loader
  cq_validation/             deterministic and LLM-assisted CQ validation
```

## Quick Start

### 1. Start Neo4j

The repository uses Docker Compose for local Neo4j.

```powershell
docker compose up -d
```

Open Neo4j Browser:

```text
http://localhost:7474
```

Default local credentials:

```text
username: neo4j
password: password
```

### 2. Install Python dependencies

Activate the virtual environment and install dependencies:

```powershell
pip install -r requirements.txt
```

Minimum required packages for the current MVP include:

```text
neo4j
pyyaml
python-dotenv
pydantic
langchain
langchain-openai
```

### 3. Set environment variables

Create a local `.env` file:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4o-mini
```

Do not commit `.env` to Git.

### 4. Set Python path

In PowerShell:

```powershell
$env:PYTHONPATH="src"
```

## Run the Current Demo

### 1. Initialize Neo4j schema

Execute the Cypher files in Neo4j Browser or with `cypher-shell`:

```text
graph/schema/01_create_constraints.cypher
graph/schema/02_init_control_graph.cypher
graph/schema/03_equipment_schema.cypher
graph/schema/04_parameter_schema.cypher
graph/schema/05_unit_vocabulary.cypher
```

### 2. Run deterministic schema validation

```powershell
python -m graph_datasheet_extractor.schema_validation.main_validation
```

Expected result:

```text
Result: PASSED
```

### 3. Run LLM-assisted schema validation

```powershell
python -m graph_datasheet_extractor.schema_validation.main_llm_validation
```

Expected result:

```text
Result: PASSED
```

### 4. Validate graph-shaped JSON

```powershell
python -m graph_datasheet_extractor.graph_representation.main_validate_graph_json
```

Expected result:

```text
Result: PASSED
```

### 5. Load sample graph into Neo4j

```powershell
python -m graph_datasheet_extractor.graph_population.main_load_sample_graph
```

Expected result:

```text
Result: PASSED
```

### 6. Run deterministic CQ validation

```powershell
python -m graph_datasheet_extractor.cq_validation.main_cq_validation
```

Expected result:

```text
Result: PASSED
```

### 7. Run LLM-assisted CQ validation

```powershell
python -m graph_datasheet_extractor.cq_validation.main_llm_cq_validation
```

Expected current behavior:

```text
CQ1–CQ4: likely pass
CQ5: may fail because it requires more complex validation logic
```

This demonstrates that LLM-generated Cypher is treated as candidate output and checked against deterministic expected results.

## Example Neo4j Queries

List extracted equipment:

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

List extracted parameters:

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

Trace parameters to evidence:

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

## Role of LangChain

LangChain is currently used for:

- LLM-assisted schema validation query generation;
- LLM-assisted CQ query generation;
- structured output with Pydantic models;
- prompt construction for controlled Cypher generation.

Planned LangChain roles include:

- graph-guided prompt construction;
- structured extraction from selected datasheet content blocks;
- output parsing and repair prompts.

## Planned Role of LangGraph

LangGraph is not yet part of the implemented MVP.

It is planned for the full stateful extraction workflow, including:

- state management;
- workflow node orchestration;
- validation branches;
- retry logic;
- repair attempts;
- optional human review;
- final report generation.

## Design References

Knowledge graphs and hallucination reduction:

1. Ernests Lavrinovics, Russa Biswas, Johannes Bjerva, Katja Hose, *Knowledge Graphs, Large Language Models, and Hallucinations: An NLP Perspective*, Journal of Web Semantics, Volume 85, 2025, 100844.
2. Agrawal et al., *Can Knowledge Graphs Reduce Hallucinations in LLMs? A Survey*, NAACL 2024.

Best-practice references:

- LangChain structured output: https://docs.langchain.com/oss/python/langchain/structured-output
- LangGraph workflow design: https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph
- Neo4j data modeling best practices: https://support.neo4j.com/s/article/360024789554-Data-Modeling-Best-Practices
- Neo4j constraints and data integrity: https://neo4j.com/graphacademy/training-best-practices-40/01-best-practices40-defining-constraints-data
- Neo4j GraphRAG Python package: https://neo4j.com/docs/neo4j-graphrag-python/current

## Roadmap

### Phase 1 — Graph backend MVP

Status: mostly complete.

- Neo4j schema and constraints;
- control/vocabulary graph;
- schema validation;
- graph-shaped JSON;
- graph JSON validation;
- Neo4j population;
- CQ validation;
- LLM-assisted Cypher generation.

### Phase 2 — Document screening

Next implementation phase.

Planned outputs:

```text
outputs/intermediate/page_texts.json
outputs/intermediate/page_scores.json
outputs/intermediate/selected_content_blocks.json
```

Planned modules:

```text
src/graph_datasheet_extractor/preprocessing/pdf_text_extractor.py
src/graph_datasheet_extractor/preprocessing/page_scorer.py
src/graph_datasheet_extractor/preprocessing/page_selector.py
src/graph_datasheet_extractor/preprocessing/content_block_builder.py
```

### Phase 3 — LangChain structured extraction

Planned goal:

```text
selected_content_blocks.json
    ↓
LangChain structured extraction
    ↓
graph-shaped JSON
```

### Phase 4 — End-to-end pipeline runner

Planned goal:

```text
datasheet PDF → screening → extraction → validation → Neo4j → CQ validation → report
```

### Phase 5 — LangGraph orchestration

Planned goal:

```text
stateful workflow with validation branches, retries, repair, and optional human review
```
