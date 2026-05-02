# Graph Model and Competency Questions

This document describes the current Neo4j graph model used in the graph-guided datasheet extraction demo.

The project follows a query-driven graph modeling approach: before defining the graph model, we define the competency questions (CQs) that the graph should be able to answer.

The goal is not to model all possible datasheet information. Instead, the MVP defines a minimal but testable Neo4j property graph that supports:

- graph-shaped JSON representation;
- evidence-grounded extraction;
- vocabulary grounding;
- Neo4j population;
- deterministic validation;
- LLM-assisted Cypher query generation;
- competency-question based inspection.

## Current Scope

The current MVP uses a manually prepared graph-shaped JSON sample for the Vishay TEMT6000X01 ambient light sensor datasheet.

The graph model is designed around two connected parts:

1. **Instance graph**  
   Stores extracted datasheet information.

2. **Control / vocabulary graph**  
   Stores concepts, relationship definitions, parameter types, units, equipment types, and required-parameter expectations.

The current implementation already supports graph-shaped JSON validation, Neo4j loading, deterministic CQ validation, and LLM-assisted CQ query generation.

---

# 1. Competency Questions

## CQ1: Which equipment was extracted from the datasheet?

This question checks whether the pipeline can identify equipment entities described by the input datasheet.

Expected graph pattern:

```cypher
(:Datasheet)-[:DESCRIBES]->(:Equipment)
(:Equipment)-[:HAS_EQUIPMENT_TYPE]->(:EquipmentType)
```

Required node labels:

- `Datasheet`
- `Equipment`
- `EquipmentType`

Required relationship types:

- `DESCRIBES`
- `HAS_EQUIPMENT_TYPE`

CQ1 also checks whether raw equipment descriptions can be grounded to a normalized equipment type vocabulary node.

---

## CQ2: Which technical parameters were extracted for each equipment?

This question checks whether extracted equipment is connected to technical parameters and whether each extracted parameter is grounded to a normalized `ParameterType`.

Expected graph pattern:

```cypher
(:Equipment)-[:HAS_PARAMETER]->(:TechnicalParameter)
(:TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(:ParameterType)
(:TechnicalParameter)-[:HAS_UNIT]->(:Unit)
```

Required node labels:

- `Equipment`
- `TechnicalParameter`
- `ParameterType`
- `Unit`

Required relationship types:

- `HAS_PARAMETER`
- `HAS_PARAMETER_TYPE`
- `HAS_UNIT`

`HAS_UNIT` is optional for string-valued or categorical parameters, such as `ProductModel`, `DeviceType`, `PackageType`, or `PackageForm`.

---

## CQ3: Which source evidence supports each extracted parameter?

This question checks whether each extracted technical parameter can be traced back to source evidence in the datasheet.

Expected graph pattern:

```cypher
(:Equipment)-[:HAS_PARAMETER]->(:TechnicalParameter)
(:TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(:ParameterType)
(:TechnicalParameter)-[:HAS_UNIT]->(:Unit)
(:TechnicalParameter)-[:EVIDENCED_BY]->(:Evidence)
```

Required node labels:

- `Equipment`
- `TechnicalParameter`
- `ParameterType`
- `Unit`
- `Evidence`

Required relationship types:

- `HAS_PARAMETER`
- `HAS_PARAMETER_TYPE`
- `HAS_UNIT`
- `EVIDENCED_BY`

Minimum MVP `Evidence` properties:

```text
id
source_document_id
page_number
content_block_id
source_text
evidence_type
confidence
evidence_status
extraction_method
```

Required MVP evidence fields:

```text
source_document_id
page_number
source_text
evidence_status
confidence
```

Allowed values for `evidence_status`:

```text
explicit
inferred
missing
ambiguous
```

This CQ supports evidence-grounded extraction and hallucination-risk inspection.

---

## CQ4: Which extracted parameters are normalized to known graph vocabulary concepts?

This question checks whether extracted parameters are grounded in the graph vocabulary.

Expected graph patterns:

```cypher
(:Equipment)-[:HAS_PARAMETER]->(:TechnicalParameter)
(:TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(:ParameterType)
(:TechnicalParameter)-[:HAS_UNIT]->(:Unit)
```

Required node labels:

- `Equipment`
- `TechnicalParameter`
- `ParameterType`
- `Unit`

Required relationship types:

- `HAS_PARAMETER`
- `HAS_PARAMETER_TYPE`
- `HAS_UNIT`

CQ4 checks two grounding dimensions:

1. parameter-type grounding;
2. unit grounding, where applicable.

Expected grounding status values:

```text
parameter_type_grounding_status:
- grounded
- not_grounded

unit_grounding_status:
- grounded
- missing_unit_grounding
- not_required
```

---

## CQ5: Which required parameters are missing or use unsupported units?

This question checks whether extracted equipment satisfies required-parameter expectations and whether extracted units are supported by the domain vocabulary.

Relevant graph patterns:

```cypher
(:Equipment)-[:HAS_PARAMETER]->(:TechnicalParameter)
(:TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(:ParameterType)
(:TechnicalParameter)-[:HAS_UNIT]->(:Unit)

(:RequiredParameter)-[:REQUIRES_PARAMETER_TYPE]->(:ParameterType)
(:ParameterType)-[:ALLOWS_UNIT]->(:Unit)
```

Required node labels:

- `Equipment`
- `TechnicalParameter`
- `ParameterType`
- `Unit`
- `RequiredParameter`

Required relationship types:

- `HAS_PARAMETER`
- `HAS_PARAMETER_TYPE`
- `HAS_UNIT`
- `REQUIRES_PARAMETER_TYPE`
- `ALLOWS_UNIT`

CQ5 detects three issue types:

```text
MISSING_REQUIRED_PARAMETER
UNSUPPORTED_UNIT
MISSING_EXPECTED_UNIT
```

In the current gold sample, CQ5 is expected to return no rows, because all required MVP parameters are present and all extracted units are supported.

---

# 2. Instance Graph

The instance graph stores extracted information from a datasheet.

## Instance Node Labels

The current MVP instance graph uses the following node labels:

```text
Datasheet
Equipment
TechnicalParameter
Evidence
ExtractionRun
ValidationIssue
```

## Instance Relationship Types

```cypher
(:Datasheet)-[:DESCRIBES]->(:Equipment)

(:Equipment)-[:HAS_PARAMETER]->(:TechnicalParameter)

(:TechnicalParameter)-[:EVIDENCED_BY]->(:Evidence)

(:TechnicalParameter)-[:GENERATED_BY]->(:ExtractionRun)

(:ValidationIssue)-[:ABOUT]->(:TechnicalParameter)
```

The instance graph does not duplicate vocabulary nodes such as `ParameterType`, `Unit`, or `EquipmentType` inside each extraction result. Instead, extracted instance nodes point to existing control/vocabulary nodes.

## Datasheet

Represents the input technical document.

Typical properties:

```text
id
file_name
document_type
manufacturer
product_model
```

Example:

```text
datasheet_vishay_temt6000x01
```

## Equipment

Represents the product or device described by the datasheet.

Typical properties:

```text
id
manufacturer
product_model
raw_equipment_type
```

Example:

```text
equipment_vishay_temt6000x01
```

## TechnicalParameter

Represents an extracted parameter value.

Typical properties:

```text
id
raw_label
value
value_type
```

Examples:

```text
Product model: TEMT6000X01
Dimensions: 4 x 2 x 1.05
Peak sensitivity: 570
Angle of half sensitivity: ±60
```

The normalized semantic type is not stored only as a string property. It is represented by:

```cypher
(:TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(:ParameterType)
```

## Evidence

Represents source evidence supporting an extracted parameter.

Typical properties:

```text
id
source_document_id
page_number
content_block_id
source_text
evidence_type
evidence_status
confidence
extraction_method
```

Evidence nodes are used to make extraction auditable and to reduce unsupported or hallucinated values.

## ExtractionRun

Represents how a parameter was generated.

Typical properties:

```text
id
method
status
description
```

The current sample uses:

```text
manual_gold_sample
```

## ValidationIssue

Represents a graph validation issue.

The current gold sample does not create validation issue nodes because it is expected to pass validation.

---

# 3. Control and Vocabulary Graph

The control/vocabulary graph stores semantic vocabulary and lightweight constraints used before and after extraction.

## Control / Vocabulary Node Labels

The current MVP uses:

```text
Concept
RelationshipDefinition
ParameterType
Unit
EquipmentType
RequiredParameter
```

Earlier design notes included `AllowedUnit` and `PropertyDefinition` as possible control nodes. In the current implementation, allowed units are represented directly by relationships:

```cypher
(:ParameterType)-[:ALLOWS_UNIT]->(:Unit)
```

`PropertyDefinition` is not yet implemented.

## Core Control Relationships

```cypher
(:RelationshipDefinition)-[:FROM_CONCEPT]->(:Concept)
(:RelationshipDefinition)-[:TO_CONCEPT]->(:Concept)

(:ParameterType)-[:INSTANCE_OF_CONCEPT]->(:Concept {name: "ParameterType"})
(:Unit)-[:INSTANCE_OF_CONCEPT]->(:Concept {name: "Unit"})
(:EquipmentType)-[:INSTANCE_OF_CONCEPT]->(:Concept {name: "Equipment"})

(:RequiredParameter)-[:REQUIRES_PARAMETER_TYPE]->(:ParameterType)

(:ParameterType)-[:ALLOWS_UNIT]->(:Unit)
```

## Vocabulary Grounding Relationships

Extracted instance nodes are connected to vocabulary nodes through these relationships:

```cypher
(:Equipment)-[:HAS_EQUIPMENT_TYPE]->(:EquipmentType)

(:TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(:ParameterType)

(:TechnicalParameter)-[:HAS_UNIT]->(:Unit)
```

These links support controlled vocabulary grounding, unit validation, and competency-question queries.

---

# 4. Relationship Definitions

The control graph stores relationship definitions as queryable nodes.

Current `RelationshipDefinition` entries:

```text
DESCRIBES
HAS_EQUIPMENT_TYPE
HAS_PARAMETER
HAS_PARAMETER_TYPE
HAS_UNIT
EVIDENCED_BY
GENERATED_BY
ABOUT
```

Each `RelationshipDefinition` has a source and target concept:

```cypher
(:RelationshipDefinition)-[:FROM_CONCEPT]->(:Concept)
(:RelationshipDefinition)-[:TO_CONCEPT]->(:Concept)
```

This makes relationship semantics inspectable and usable for future prompt construction.

---

# 5. Current MVP Vocabulary

## EquipmentType Vocabulary

Current equipment type vocabulary:

```text
AmbientLightSensor
DigitalAccelerometer
```

`AmbientLightSensor` is used by the primary MVP datasheet:

```text
Vishay TEMT6000X01
```

`DigitalAccelerometer` is included as a variation candidate for the planned ADXL345 datasheet case.

## ParameterType Vocabulary

Current `ParameterType` vocabulary:

```text
Manufacturer
ProductModel
DeviceType
PackageType
PackageForm
Dimensions
PeakSensitivityWavelength
AngleOfHalfSensitivity
```

Each `ParameterType` may include metadata such as:

```text
display_name
description
value_type
priority
parameter_category
expects_unit
screening_weight
extraction_hint
aliases
screening_keywords
```

Examples:

```text
PeakSensitivityWavelength
  value_type: number
  parameter_category: optical
  expects_unit: true

ProductModel
  value_type: string
  parameter_category: identification
  expects_unit: false
```

## Unit Vocabulary

Current MVP and variation unit vocabulary:

```text
mm
nm
degree
g
bit
V
µA
°C
```

Primary MVP units:

```text
mm
nm
degree
```

Variation units:

```text
g
bit
V
µA
°C
```

## Allowed Units

Current `ALLOWS_UNIT` links:

```cypher
(:ParameterType {name: "Dimensions"})-[:ALLOWS_UNIT]->(:Unit {symbol: "mm"})

(:ParameterType {name: "PeakSensitivityWavelength"})-[:ALLOWS_UNIT]->(:Unit {symbol: "nm"})

(:ParameterType {name: "AngleOfHalfSensitivity"})-[:ALLOWS_UNIT]->(:Unit {symbol: "degree"})
```

String-valued and categorical parameters intentionally do not require units.

## Required Parameters

Current MVP required parameters:

```text
ProductModel
DeviceType
PackageForm
Dimensions
PeakSensitivityWavelength
```

Represented as:

```cypher
(:RequiredParameter)-[:REQUIRES_PARAMETER_TYPE]->(:ParameterType)
```

These required parameters are used by CQ5 and validation logic.

---

# 6. Graph-shaped JSON and `target_ref`

The graph-shaped JSON format separates extracted instance nodes from existing vocabulary/control nodes.

Instance nodes are created in the JSON `nodes` list.

Vocabulary/control nodes are referenced through `target_ref`.

## Local target relationship

Use `target` when the target node is defined in the same graph-shaped JSON document.

Example:

```json
{
  "source": "equipment_vishay_temt6000x01",
  "type": "HAS_PARAMETER",
  "target": "param_dimensions_001"
}
```

## Vocabulary target relationship

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

```cypher
MATCH (target:ParameterType {name: "Dimensions"})
```

then create:

```cypher
(:TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(:ParameterType)
```

Supported `target_ref` patterns:

```text
HAS_PARAMETER_TYPE → ParameterType.name
HAS_UNIT → Unit.symbol
HAS_EQUIPMENT_TYPE → EquipmentType.name
```

See also:

```text
docs/graph_json_format.md
```

---

# 7. Validation and Query Files

## Schema and Vocabulary Initialization

Neo4j schema and vocabulary initialization files are stored in:

```text
graph/schema/
```

Current files:

```text
01_create_constraints.cypher
02_init_control_graph.cypher
03_equipment_schema.cypher
04_parameter_schema.cypher
05_unit_vocabulary.cypher
```

## Human-readable CQ Queries

Interactive CQ queries are stored in:

```text
graph/queries/
```

These are intended for manual inspection in Neo4j Browser.

## Deterministic CQ Validation Queries

Automated CQ validation queries are stored in:

```text
graph/cq_validation_queries/
```

These are compared against:

```text
validation_specs/expected_cq_results.json
```

## Schema Validation Queries

Automated schema validation queries are stored in:

```text
graph/schema_validation_queries/
```

These are compared against:

```text
validation_specs/expected_schema_state.json
```

---

# 8. Design Boundary

The MVP graph model intentionally remains lightweight.

It does not aim to represent all possible details of electronic components or sensor datasheets. Instead, it provides the minimum graph structure required to support:

- graph-guided document screening;
- graph-shaped JSON extraction output;
- evidence-grounded parameter representation;
- vocabulary grounding;
- Neo4j graph population;
- Cypher-based validation;
- deterministic CQ validation;
- LLM-assisted Cypher query generation.

Later extensions may add:

- PDF text extraction;
- document screening;
- automatic LLM extraction;
- LangGraph orchestration;
- repair/retry logic;
- HTML reporting;
- GraphRAG;
- multimodal extraction.

## Summary

The current graph model is intentionally small but complete enough to support a runnable backend pipeline:

```text
graph-shaped JSON
    ↓
Pydantic validation
    ↓
Neo4j loading
    ↓
CQ validation
    ↓
LLM-assisted CQ query generation
```

This design keeps the MVP auditable and testable while leaving clear extension points for full document processing and LLM extraction.
