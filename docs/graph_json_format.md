# Graph-shaped JSON Format

This document defines the graph-shaped JSON exchange format used in this repository.

The graph-shaped JSON format is the intermediate representation between LLM-based information extraction and Neo4j graph population.

It is designed to preserve graph semantics explicitly by representing extracted information as nodes and relationships, instead of using flat key-value extraction output.

## Purpose

The graph-shaped JSON format is used to:

- store manually prepared gold extraction samples;
- define the expected structure of LLM extraction output;
- validate extracted information before writing to Neo4j;
- distinguish extracted instance nodes from existing vocabulary/control graph nodes;
- support evidence-grounded and vocabulary-grounded graph population.

The current MVP example is stored in:

```text
data/gold/sample_graph_extraction.json
```

## Top-level Structure

A graph-shaped JSON document has the following top-level fields:

```json
{
  "schema_version": "0.1.0",
  "document_id": "datasheet_vishay_temt6000x01",
  "source_file": "data/raw/vishay_temt6000x01_datasheet.pdf",
  "extraction_scope": "manual_gold_sample",
  "description": "Manually prepared graph-shaped extraction sample.",
  "nodes": [],
  "relationships": []
}
```

## Top-level Fields

### `schema_version`

The version of the graph-shaped JSON format.

Example:

```json
"schema_version": "0.1.0"
```

This allows the format to evolve while keeping older examples interpretable.

### `document_id`

Stable identifier of the input document.

Example:

```json
"document_id": "datasheet_vishay_temt6000x01"
```

The `document_id` should match the `id` of the `Datasheet` node in the `nodes` list.

### `source_file`

Local path to the input datasheet file.

Example:

```json
"source_file": "data/raw/vishay_temt6000x01_datasheet.pdf"
```

The file may be ignored by Git if it is a third-party datasheet.

### `extraction_scope`

Describes how the JSON was produced.

Example values:

```text
manual_gold_sample
llm_generated
llm_repaired
human_reviewed
```

### `description`

Optional human-readable description of the graph-shaped extraction.

### `nodes`

List of nodes created by this extraction result.

### `relationships`

List of relationships created by this extraction result.

---

# Node Object

Each node object represents one graph node to be created or merged into Neo4j.

## Node Structure

```json
{
  "id": "param_dimensions_001",
  "labels": ["TechnicalParameter"],
  "properties": {
    "raw_label": "Dimensions",
    "value": "4 x 2 x 1.05",
    "value_type": "dimension_tuple"
  }
}
```

## Required Node Fields

### `id`

Stable local node identifier.

The `id` is used by relationships inside the same graph-shaped JSON document.

Example:

```json
"id": "param_dimensions_001"
```

### `labels`

List of Neo4j labels assigned to the node.

Example:

```json
"labels": ["TechnicalParameter"]
```

The MVP expects one primary label per node, but the format allows multiple labels.

### `properties`

Map of node properties.

Example:

```json
"properties": {
  "raw_label": "Dimensions",
  "value": "4 x 2 x 1.05",
  "value_type": "dimension_tuple"
}
```

## MVP Node Labels

The MVP graph-shaped JSON may contain extracted instance nodes with the following labels:

```text
Datasheet
Equipment
TechnicalParameter
Evidence
ExtractionRun
ValidationIssue
```

In the current sample, vocabulary nodes such as `ParameterType`, `Unit`, and `EquipmentType` are usually not recreated in `nodes`. They are referenced through `target_ref`.

---

# Relationship Object

Each relationship object represents one graph relationship.

There are two types of relationship targets:

1. `target`: target is another node inside the same graph-shaped JSON document.
2. `target_ref`: target is an existing node in the Neo4j control/vocabulary graph.

Exactly one of `target` or `target_ref` should be used.

---

## Relationship with `target`

Use `target` when the target node is defined in the same JSON document.

Example:

```json
{
  "source": "equipment_vishay_temt6000x01",
  "type": "HAS_PARAMETER",
  "target": "param_dimensions_001"
}
```

This means:

```text
(:Equipment)-[:HAS_PARAMETER]->(:TechnicalParameter)
```

where both nodes are present in the `nodes` list.

## Required Fields

### `source`

The `id` of the source node in the `nodes` list.

### `type`

The Neo4j relationship type.

### `target`

The `id` of the target node in the `nodes` list.

---

## Relationship with `target_ref`

Use `target_ref` when the target node already exists in the Neo4j control/vocabulary graph.

Example:

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

This means:

```text
Find (:ParameterType {name: "Dimensions"}) in Neo4j,
then create:
(:TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(:ParameterType)
```

## `target_ref` Structure

```json
{
  "label": "ParameterType",
  "key": "name",
  "value": "Dimensions"
}
```

### `label`

Neo4j label of the referenced node.

Example values:

```text
ParameterType
Unit
EquipmentType
```

### `key`

Property used to identify the referenced node.

Example values:

```text
name
symbol
```

### `value`

Expected property value.

Examples:

```text
Dimensions
nm
AmbientLightSensor
```

## Examples

### ParameterType reference

```json
{
  "source": "param_peak_sensitivity_wavelength_001",
  "type": "HAS_PARAMETER_TYPE",
  "target_ref": {
    "label": "ParameterType",
    "key": "name",
    "value": "PeakSensitivityWavelength"
  }
}
```

### Unit reference

```json
{
  "source": "param_peak_sensitivity_wavelength_001",
  "type": "HAS_UNIT",
  "target_ref": {
    "label": "Unit",
    "key": "symbol",
    "value": "nm"
  }
}
```

### EquipmentType reference

```json
{
  "source": "equipment_vishay_temt6000x01",
  "type": "HAS_EQUIPMENT_TYPE",
  "target_ref": {
    "label": "EquipmentType",
    "key": "name",
    "value": "AmbientLightSensor"
  }
}
```

---

# Why `target_ref` Is Needed

The graph-shaped JSON separates two kinds of nodes.

## Extracted instance nodes

These are created by the extraction result.

Examples:

```text
Datasheet
Equipment
TechnicalParameter
Evidence
ExtractionRun
```

They are included in the `nodes` list.

## Existing vocabulary/control graph nodes

These are created by the schema initialization Cypher files.

Examples:

```text
ParameterType
Unit
EquipmentType
```

They should not be duplicated by each extraction result.

Instead, extracted nodes should point to them through `target_ref`.

This supports vocabulary grounding and avoids duplicate vocabulary nodes.

---

# Design Rules

## Rule 1 — Every node must have a stable `id`

Every node in `nodes` must have a unique `id`.

The `id` is used for internal relationship references.

## Rule 2 — Each relationship must have exactly one target form

A relationship must use either:

```json
"target": "node_id"
```

or:

```json
"target_ref": {
  "label": "...",
  "key": "...",
  "value": "..."
}
```

It must not use both.

## Rule 3 — `target` must refer to a node in the same JSON document

If a relationship uses `target`, the target value must match an existing node `id` in `nodes`.

## Rule 4 — `target_ref` must refer to an existing Neo4j vocabulary/control node

If a relationship uses `target_ref`, the referenced node should already exist in Neo4j.

For example:

```json
"target_ref": {
  "label": "Unit",
  "key": "symbol",
  "value": "nm"
}
```

requires Neo4j to contain:

```cypher
(:Unit {symbol: "nm"})
```

## Rule 5 — TechnicalParameter nodes should have ParameterType grounding

Every `TechnicalParameter` should normally have:

```text
(:TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(:ParameterType)
```

represented through `target_ref`.

## Rule 6 — Physical TechnicalParameter nodes should have Unit grounding

If the corresponding `ParameterType` expects a unit, the `TechnicalParameter` should have:

```text
(:TechnicalParameter)-[:HAS_UNIT]->(:Unit)
```

represented through `target_ref`.

String-valued or categorical parameters may not require a unit.

## Rule 7 — TechnicalParameter nodes should have Evidence

Every extracted `TechnicalParameter` should have:

```text
(:TechnicalParameter)-[:EVIDENCED_BY]->(:Evidence)
```

This supports traceability and hallucination-risk detection.

## Rule 8 — TechnicalParameter nodes should have ExtractionRun

Every extracted `TechnicalParameter` should have:

```text
(:TechnicalParameter)-[:GENERATED_BY]->(:ExtractionRun)
```

This records how the parameter was produced.

---

# Evidence Node Format

Evidence nodes store source provenance for extracted values.

Example:

```json
{
  "id": "evidence_peak_sensitivity_wavelength_001",
  "labels": ["Evidence"],
  "properties": {
    "source_document_id": "datasheet_vishay_temt6000x01",
    "page_number": 1,
    "content_block_id": "page_1_features",
    "source_text": "Peak sensitivity: 570 nm",
    "evidence_type": "feature_list",
    "evidence_status": "explicit",
    "confidence": 0.95,
    "extraction_method": "manual_gold_sample"
  }
}
```

## Required MVP Evidence Properties

```text
source_document_id
page_number
source_text
evidence_status
confidence
```

## Recommended Evidence Properties

```text
content_block_id
evidence_type
extraction_method
```

## Evidence Status Values

Recommended values:

```text
explicit
inferred
missing
ambiguous
```

For MVP auto-population, `explicit` evidence is preferred.

---

# TechnicalParameter Node Format

TechnicalParameter nodes store extracted parameter values.

Example:

```json
{
  "id": "param_peak_sensitivity_wavelength_001",
  "labels": ["TechnicalParameter"],
  "properties": {
    "raw_label": "Peak sensitivity",
    "value": 570,
    "value_type": "number"
  }
}
```

## Recommended TechnicalParameter Properties

```text
raw_label
value
value_type
```

The normalized parameter type is not stored only as a string property. It is represented by a relationship to a `ParameterType` vocabulary node.

---

# Minimal Valid Example

```json
{
  "schema_version": "0.1.0",
  "document_id": "datasheet_demo",
  "source_file": "data/raw/demo.pdf",
  "extraction_scope": "manual_gold_sample",
  "nodes": [
    {
      "id": "datasheet_demo",
      "labels": ["Datasheet"],
      "properties": {
        "file_name": "demo.pdf"
      }
    },
    {
      "id": "equipment_demo",
      "labels": ["Equipment"],
      "properties": {
        "product_model": "DEMO"
      }
    },
    {
      "id": "param_demo_001",
      "labels": ["TechnicalParameter"],
      "properties": {
        "raw_label": "Peak sensitivity",
        "value": 570,
        "value_type": "number"
      }
    },
    {
      "id": "evidence_demo_001",
      "labels": ["Evidence"],
      "properties": {
        "source_document_id": "datasheet_demo",
        "page_number": 1,
        "source_text": "Peak sensitivity: 570 nm",
        "evidence_status": "explicit",
        "confidence": 0.95
      }
    }
  ],
  "relationships": [
    {
      "source": "datasheet_demo",
      "type": "DESCRIBES",
      "target": "equipment_demo"
    },
    {
      "source": "equipment_demo",
      "type": "HAS_PARAMETER",
      "target": "param_demo_001"
    },
    {
      "source": "param_demo_001",
      "type": "HAS_PARAMETER_TYPE",
      "target_ref": {
        "label": "ParameterType",
        "key": "name",
        "value": "PeakSensitivityWavelength"
      }
    },
    {
      "source": "param_demo_001",
      "type": "HAS_UNIT",
      "target_ref": {
        "label": "Unit",
        "key": "symbol",
        "value": "nm"
      }
    },
    {
      "source": "param_demo_001",
      "type": "EVIDENCED_BY",
      "target": "evidence_demo_001"
    }
  ]
}
```

---

# Validation Expectations

The graph-shaped JSON validator should check:

- top-level fields exist;
- node IDs are unique;
- node labels are non-empty;
- relationship sources exist in `nodes`;
- relationship targets exist when `target` is used;
- exactly one of `target` or `target_ref` is used;
- `target_ref` contains `label`, `key`, and `value`;
- every `TechnicalParameter` has `HAS_PARAMETER_TYPE`;
- every `TechnicalParameter` has `EVIDENCED_BY`;
- every `TechnicalParameter` has `GENERATED_BY`, unless explicitly configured otherwise.

Later validators may also check whether `target_ref` actually exists in Neo4j.

---

# Summary

The graph-shaped JSON format is designed to keep LLM extraction output explicit, auditable, and graph-ready.

Instead of returning flat fields such as:

```json
{
  "peak_sensitivity": "570 nm"
}
```

the extraction result returns graph elements:

```text
TechnicalParameter
  → ParameterType
  → Unit
  → Evidence
  → ExtractionRun
```

This design supports:

- vocabulary grounding;
- source evidence tracking;
- graph validation before database population;
- controlled Neo4j graph loading;
- later LangGraph workflow integration.
