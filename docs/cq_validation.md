# Competency Question Validation

This document explains how competency-question (CQ) validation is implemented in this repository.

CQ validation checks whether the populated Neo4j instance graph can answer the project-specific questions that the graph model was designed for. It is different from schema validation: schema validation checks the control/vocabulary graph, while CQ validation checks the extracted instance graph after graph-shaped JSON has been loaded into Neo4j.

## Purpose

The CQ validation layer has three goals:

1. Verify that the manually prepared graph-shaped JSON sample was loaded into Neo4j correctly.
2. Check that the populated graph can answer the expected competency questions.
3. Demonstrate a controlled use of LLM-generated Cypher queries, where generated queries are treated as candidates and checked against deterministic expected results.

## Current Competency Questions

The current MVP defines five competency questions:

```text
CQ1: Which equipment was extracted from the datasheet?
CQ2: Which technical parameters were extracted for each equipment?
CQ3: Which source evidence supports each extracted parameter?
CQ4: Which extracted parameters are normalized to known graph vocabulary concepts?
CQ5: Which required parameters are missing or use unsupported units?
```

The first four CQs are mainly retrieval and inspection queries. CQ5 is a validation-style query that checks whether required parameters are missing, whether extracted units are unsupported, and whether expected units are missing.

## Graph Context

The CQ validation queries are evaluated over the populated Neo4j graph.

The main instance graph pattern is:

```text
(:Datasheet)-[:DESCRIBES]->(:Equipment)
(:Equipment)-[:HAS_PARAMETER]->(:TechnicalParameter)
(:TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(:ParameterType)
(:TechnicalParameter)-[:HAS_UNIT]->(:Unit)
(:TechnicalParameter)-[:EVIDENCED_BY]->(:Evidence)
(:TechnicalParameter)-[:GENERATED_BY]->(:ExtractionRun)
```

The current control/vocabulary graph also includes:

```text
(:Equipment)-[:HAS_EQUIPMENT_TYPE]->(:EquipmentType)
(:RequiredParameter)-[:REQUIRES_PARAMETER_TYPE]->(:ParameterType)
(:ParameterType)-[:ALLOWS_UNIT]->(:Unit)
```

## Validation Input Files

CQ validation uses the following files:

```text
validation_specs/expected_cq_results.json
validation_specs/cq_validation_targets.yaml
```

### `expected_cq_results.json`

This file stores the expected result rows for each CQ.

It acts as the local ground truth, or "soll output", for the sample graph.

Example structure:

```json
{
  "cq1_extracted_equipment": [
    {
      "datasheet_id": "datasheet_vishay_temt6000x01",
      "equipment_id": "equipment_vishay_temt6000x01",
      "product_model": "TEMT6000X01",
      "normalized_equipment_type": "AmbientLightSensor"
    }
  ],
  "cq5_required_parameter_status": []
}
```

CQ5 is expected to return an empty list for the current gold sample, because the sample graph is complete and does not contain missing required parameters or unsupported units.

### `cq_validation_targets.yaml`

This file describes the validation targets for deterministic and LLM-assisted CQ validation.

Each target defines:

```text
check_id
description
expected_result_key
allowed_query_type
instruction
```

The `instruction` field is used by the LLM-assisted CQ query generator. It provides the competency-question goal, relevant graph semantics, required output columns, and constraints such as "return only scalar properties".

## Deterministic CQ Validation

Deterministic CQ validation uses hand-written Cypher queries.

The queries are stored in:

```text
graph/cq_validation_queries/
├─ cq1_extracted_equipment.cypher
├─ cq2_technical_parameters.cypher
├─ cq3_parameter_evidence.cypher
├─ cq4_vocabulary_grounding.cypher
└─ cq5_required_parameter_status.cypher
```

The Python runner executes each query against Neo4j and compares the actual result with the expected result in:

```text
validation_specs/expected_cq_results.json
```

The implementation is located in:

```text
src/graph_datasheet_extractor/cq_validation/
├─ expected_cq_loader.py
├─ cq_result_comparator.py
├─ cq_validation_runner.py
└─ main_cq_validation.py
```

### Run deterministic CQ validation

Before running CQ validation, the sample graph must be loaded into Neo4j:

```powershell
$env:PYTHONPATH="src"
python -m graph_datasheet_extractor.graph_population.main_load_sample_graph
```

Then run:

```powershell
$env:PYTHONPATH="src"
python -m graph_datasheet_extractor.cq_validation.main_cq_validation
```

Expected result:

```text
=== Deterministic CQ Validation Summary ===
Total checks : 5
Passed checks: 5
Failed checks: 0

Result: PASSED
```

The report is written to:

```text
outputs/validation_reports/cq_validation_report.json
```

## LLM-assisted CQ Validation

LLM-assisted CQ validation uses LangChain to generate read-only Cypher queries from the CQ validation targets.

The generated queries are not trusted directly. They are processed through the following steps:

```text
cq_validation_targets.yaml
        ↓
LangChain LLM generates CQ Cypher
        ↓
read-only safety checker
        ↓
Neo4j execution
        ↓
actual result rows
        ↓
comparison with expected_cq_results.json
        ↓
validation report
```

The implementation is located in:

```text
src/graph_datasheet_extractor/cq_validation/
├─ llm_cq_generator.py
├─ main_generate_cq.py
├─ llm_cq_validation_runner.py
└─ main_llm_cq_validation.py
```

### Safety principle

LLM-generated Cypher is treated as untrusted candidate code.

The safety checker rejects write or database-modifying operations such as:

```text
CREATE
MERGE
DELETE
DETACH DELETE
SET
REMOVE
DROP
CALL
LOAD CSV
FOREACH
CREATE CONSTRAINT
CREATE INDEX
```

The LLM is instructed to return only scalar properties, not full Neo4j nodes, relationships, or paths.

### Run LLM-assisted CQ validation

```powershell
$env:PYTHONPATH="src"
python -m graph_datasheet_extractor.cq_validation.main_llm_cq_validation
```

The reports are written to:

```text
outputs/validation_reports/llm_cq_validation_report.json
outputs/validation_reports/llm_generated_cq_queries.json
```

## Current LLM-assisted Result

In the current implementation, the LLM-assisted CQ validation behaves as follows:

```text
CQ1: likely passes after schema-constrained prompting
CQ2: likely passes after schema-constrained prompting
CQ3: likely passes after schema-constrained prompting
CQ4: likely passes after schema-constrained prompting
CQ5: may fail because it requires complex validation logic
```

This is an intentional and useful result.

CQ1–CQ4 are retrieval-style queries. They ask the graph to list equipment, parameters, evidence, and vocabulary grounding. These are suitable for LLM-assisted Cypher generation when the prompt includes sufficient schema context.

CQ5 is different. It is a validation-style query requiring several logical cases:

1. missing required parameters;
2. unsupported units;
3. missing expected units.

It may require `UNION`, `NOT EXISTS`, and careful handling of empty results. This makes it more brittle for unconstrained LLM query generation.

## Why CQ5 May Fail

CQ5 is harder because it is not only a retrieval query. It encodes validation logic.

The query must detect:

```text
RequiredParameter → ParameterType
Equipment → TechnicalParameter → ParameterType
TechnicalParameter → Unit
ParameterType → Allowed Unit
ParameterType.expects_unit = true
```

and combine multiple negative conditions:

```text
required parameter does not exist
unit exists but is not allowed
unit is expected but missing
```

For this reason, CQ5 is better maintained as a deterministic baseline query or a template-guided validation rule.

The LLM-assisted CQ5 result is therefore useful as a limitation case: it shows that complex validation logic should not be blindly delegated to an LLM.

## Design Interpretation

The CQ validation design follows this principle:

```text
LLM generates candidate Cypher.
Neo4j executes only read-only queries.
Deterministic comparison decides pass/fail.
```

This means the LLM is not the final judge.

The validation system can catch:

- missing output columns;
- wrong aliases;
- invented property names;
- undefined variables;
- wrong graph traversal paths;
- syntactically invalid Cypher;
- semantically incorrect result rows.

This is important for a graph-guided extraction system because it prevents plausible-looking LLM-generated Cypher from being accepted without verification.

## Relation to Other Validation Layers

CQ validation is one layer in the wider validation stack.

```text
Neo4j constraints
    ↓
schema/control graph validation
    ↓
graph-shaped JSON validation
    ↓
Neo4j graph population
    ↓
CQ validation
    ↓
LLM-assisted CQ validation
```

Each layer checks a different type of correctness:

| Layer | Checks |
|---|---|
| Neo4j constraints | uniqueness and basic data integrity |
| schema validation | control/vocabulary graph initialization |
| graph JSON validation | structure of graph-shaped extraction output |
| graph population | whether graph-shaped JSON can be loaded into Neo4j |
| deterministic CQ validation | whether the populated graph answers CQs correctly |
| LLM-assisted CQ validation | whether LLM-generated Cypher can reproduce expected CQ answers |

## Typical Development Workflow

During development, use this sequence:

```powershell
$env:PYTHONPATH="src"

python -m graph_datasheet_extractor.graph_population.main_load_sample_graph
python -m graph_datasheet_extractor.cq_validation.main_cq_validation
python -m graph_datasheet_extractor.cq_validation.main_llm_cq_validation
```

The deterministic CQ validation should pass before relying on LLM-assisted CQ validation.

## Summary

CQ validation demonstrates that the current graph backend is not only populated, but also queryable and testable.

The deterministic CQ validation proves that the sample graph can answer the intended competency questions.

The LLM-assisted CQ validation demonstrates controlled use of LLM-generated Cypher: it can generate useful candidate queries for retrieval-style CQs, while the deterministic validation layer catches failures in more complex validation logic.
