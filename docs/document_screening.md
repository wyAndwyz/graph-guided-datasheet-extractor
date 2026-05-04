# Document Screening Pipeline

This document describes the planned document screening pipeline for the `graph-guided-datasheet-extractor` project.

The current Phase 1 MVP starts from a manually prepared graph-shaped JSON file and validates the graph backend. Phase 2 extends the project one step earlier in the workflow: from a raw PDF datasheet to selected, task-relevant content blocks.

The goal of this phase is **not** to perform LLM-based extraction yet. Instead, the goal is to build a local, deterministic preprocessing layer that reduces the amount of document content passed to the LLM later.

## Motivation

A common but weak approach to LLM-based document extraction is to send the whole PDF text to an LLM and ask for structured information.

This project intentionally avoids that design.

Technical datasheets often contain many pages, repeated tables, legal notes, ordering codes, packaging information, diagrams, revision notes, and manufacturer-specific formatting. Not all pages are equally useful for extracting the target parameters.

The screening pipeline is introduced to:

- reduce token cost;
- reduce irrelevant context passed to the LLM;
- reduce hallucination risk;
- preserve evidence grounding at page and content-block level;
- make later extraction more auditable;
- use the knowledge graph not only as a backend, but also as a semantic control layer before extraction.

In this project, the knowledge graph is expected to guide **what should be looked for** before the LLM is called.

## Position in the Overall Pipeline

The current Phase 1 MVP starts here:

```text
manual graph-shaped JSON
    ↓
graph JSON validation
    ↓
Neo4j graph population
    ↓
CQ validation
```

Phase 2 adds the document screening part before LLM extraction:

```text
PDF datasheet
    ↓
page-level text extraction
    ↓
graph-guided page scoring
    ↓
page selection
    ↓
content block construction
    ↓
selected_content_blocks.json
```

The output of Phase 2 will later become the input of Phase 3:

```text
selected_content_blocks.json
    ↓
LangChain structured extraction
    ↓
graph-shaped JSON
```

## Scope of Phase 2

Phase 2 focuses on local preprocessing and deterministic screening.

Implemented in this phase:

```text
PDF text extraction
page-level text representation
target vocabulary loading
page scoring
page selection
content block construction
intermediate JSON outputs
```

Not implemented in this phase:

```text
LLM extraction
graph-shaped JSON generation from PDF content
Neo4j loading of extracted results
LangGraph workflow orchestration
automatic repair or retry logic
HTML report generation
```

Those parts belong to later phases.

## Planned Module Structure

The planned preprocessing module is:

```text
src/graph_datasheet_extractor/preprocessing/
├─ __init__.py
├─ pdf_text_extractor.py
├─ page_scorer.py
├─ page_selector.py
└─ content_block_builder.py
```

### pdf_text_extractor.py

Responsible for extracting page-level text from a local PDF file.

Expected input:

```text
data/raw/vishay_temt6000x01_datasheet.pdf
```

Expected output:

```text
outputs/intermediate/page_texts.json
```

The output should preserve page numbers because later extraction evidence must be traceable back to the original datasheet page.

### page_scorer.py

Responsible for assigning relevance scores to pages.

The scoring should use local rules and graph vocabulary, for example:

- target parameter names;
- known aliases;
- unit symbols;
- equipment type terms;
- section headings;
- table-related keywords;
- datasheet-specific but non-LLM heuristics.

The page scorer should not call the LLM.

Expected output:

```text
outputs/intermediate/page_scores.json
```

### page_selector.py

Responsible for selecting the most relevant pages based on scores and threshold logic.

Possible selection strategies:

```text
top-k pages
minimum score threshold
always-include first page
always-include pages containing target parameter aliases
```

The exact strategy can remain simple in the first implementation.

### content_block_builder.py

Responsible for converting selected pages into content blocks that can later be passed to a LangChain extraction chain.

Expected output:

```text
outputs/intermediate/selected_content_blocks.json
```

The content block format should preserve:

- source file;
- page number;
- block id;
- text;
- matched keywords;
- screening score;
- reason for selection.

## Planned Intermediate Outputs

### page_texts.json

Example structure:

```json
{
  "source_file": "data/raw/vishay_temt6000x01_datasheet.pdf",
  "pages": [
    {
      "page_number": 1,
      "text": "..."
    },
    {
      "page_number": 2,
      "text": "..."
    }
  ]
}
```

### page_scores.json

Example structure:

```json
{
  "source_file": "data/raw/vishay_temt6000x01_datasheet.pdf",
  "scores": [
    {
      "page_number": 1,
      "score": 8.5,
      "matched_terms": ["TEMT6000X01", "ambient light sensor", "dimensions"],
      "selection_reasons": [
        "contains product model",
        "contains equipment type",
        "contains target parameter alias"
      ]
    }
  ]
}
```

### selected_content_blocks.json

Example structure:

```json
{
  "source_file": "data/raw/vishay_temt6000x01_datasheet.pdf",
  "blocks": [
    {
      "block_id": "block_page_1_full",
      "page_number": 1,
      "text": "...",
      "score": 8.5,
      "matched_terms": ["TEMT6000X01", "dimensions"],
      "selection_reasons": [
        "contains product model",
        "contains target parameter alias"
      ]
    }
  ]
}
```

## Graph-guided Screening Logic

The screening logic should be guided by the control vocabulary already represented in Neo4j and validation specs.

For the current MVP datasheet, useful target concepts include:

```text
Equipment
EquipmentType
TechnicalParameter
ParameterType
Unit
Evidence
ExtractionRun
```

The initial parameter vocabulary can include terms such as:

```text
Dimensions
Peak Sensitivity Wavelength
Angle of Half Sensitivity
Collector-Emitter Voltage
Operating Temperature
```

The unit vocabulary can include symbols such as:

```text
mm
nm
deg
V
°C
```

The screening phase should use these terms and aliases to identify potentially relevant pages.

## Why This Is Graph-guided

The screening pipeline is graph-guided because it does not only search for arbitrary keywords. It uses the expected graph structure and vocabulary to decide which pages are likely to contain extractable information.

For example, if the graph expects a `TechnicalParameter` node normalized to a known `ParameterType`, then the screening process should search for:

```text
parameter type labels
parameter aliases
allowed units
table headings
nearby value patterns
```

This creates a bridge between the graph backend and the document front end.

The graph is therefore used in two ways:

```text
before extraction: guide document screening
after extraction: validate and query extracted information
```

## First Implementation Strategy

The first implementation should stay simple and deterministic.

Recommended first version:

1. Extract text page by page from the PDF.
2. Define a small local vocabulary dictionary for the TEMT6000X01 datasheet.
3. Score each page by matched target terms and units.
4. Select the top pages.
5. Write selected full-page content blocks to JSON.
6. Do not call an LLM yet.

The first version does not need advanced layout detection.

A later version can add:

- table detection;
- section splitting;
- bounding boxes;
- OCR fallback;
- multimodal extraction;
- graph-retrieval-assisted prompt construction.

## Recommended Initial Scoring Rules

A simple first scoring rule can assign weights such as:

```text
product model match: +3
equipment type match: +2
parameter type label match: +2
parameter alias match: +2
unit symbol match: +1
table keyword match: +1
ordering/package/legal-only page penalty: -2
```

The exact weights can be tuned after inspecting the first output.

The goal is not to produce a perfect ranking. The goal is to select a small set of relevant pages while avoiding obvious irrelevant pages.

## Expected Phase 2 Success Criteria

Phase 2 can be considered complete when:

```text
1. A PDF datasheet can be read locally.
2. Page-level text is exported to page_texts.json.
3. Pages are scored using deterministic graph/vocabulary-guided rules.
4. Page scores are exported to page_scores.json.
5. Relevant pages are selected.
6. Selected content blocks are exported to selected_content_blocks.json.
7. The selected blocks are small enough to be used as input for later LLM extraction.
8. Page numbers and source text are preserved for evidence grounding.
```

## Relation to Later LLM Extraction

The selected content blocks will later be passed to LangChain structured extraction.

The later extraction step should not need to read the full PDF. Instead, it should receive:

```text
target graph schema context
allowed vocabulary
selected content blocks
expected output schema
```

This supports the main design idea of the project:

```text
knowledge graph → controls extraction target and vocabulary
screening → reduces irrelevant document context
LLM → extracts structured information from selected evidence
graph-shaped JSON → validates and loads results into Neo4j
```

## Notes

The screening pipeline should remain independent from OpenAI or any other LLM provider.

This makes Phase 2 easy to test, cheap to run, and suitable as a stable preprocessing layer before introducing LLM-based extraction.
