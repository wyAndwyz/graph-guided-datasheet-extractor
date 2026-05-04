# Layout Analysis

This document describes the planned layout analysis layer for the `graph-guided-datasheet-extractor` project.

Layout analysis is introduced as a formal step between PDF text extraction and LLM-based information extraction. Its purpose is to preserve document structure, identify meaningful content regions, and provide better evidence grounding for later extraction.

## Why Layout Analysis Is Needed

Technical datasheets are not plain text documents.

They often contain:

- title areas;
- product summaries;
- feature lists;
- parameter tables;
- absolute maximum rating tables;
- basic characteristic tables;
- package dimension drawings;
- reflow profiles;
- graphs and curves;
- ordering information;
- tape/reel packaging information;
- legal disclaimers.

A simple page-level text extraction step can recover textual content, but it does not preserve enough information about the document structure.

For example, a page-level text extractor may flatten:

```text
PARAMETER TEST CONDITION SYMBOL VALUE UNIT
Collector emitter voltage VCEO 6 V
```

into plain text. This is useful, but not enough to know whether a value came from a table row, a heading, a figure caption, or repeated page boilerplate.

Therefore, this project introduces layout analysis before LLM extraction.

## Position in the Pipeline

The earlier Phase 2 pipeline was:

```text
PDF datasheet
    ↓
page-level text extraction
    ↓
page scoring
    ↓
page selection
    ↓
selected content blocks
```

The updated layout-aware pipeline is:

```text
PDF datasheet
    ↓
page-level text extraction
    ↓
layout analysis / document parsing
    ↓
rule-based and LLM-based page scoring
    ↓
page score comparison
    ↓
page selection
    ↓
layout-aware content block building
    ↓
selected_content_blocks.json
```

Later, Phase 3 will consume the selected content blocks:

```text
selected_content_blocks.json
    ↓
LangChain structured extraction
    ↓
raw evidence-rich extraction result
    ↓
Python unit normalization and vocabulary mapping
    ↓
graph-shaped JSON
```

## Design Goal

The layout analysis layer should make later extraction more reliable by preserving:

- page number;
- reading order;
- block type;
- section or table context;
- raw text;
- optional bounding box information;
- evidence source identifiers.

The goal is not to perfectly reconstruct the PDF in the first implementation.

The first goal is to produce a stable intermediate representation that downstream steps can consume.

## Backend-Agnostic Design

The layout analysis layer should be implemented with an adapter-based design.

Different layout/document parsing backends can be used later without changing the downstream pipeline.

Planned structure:

```text
src/graph_datasheet_extractor/layout_analysis/
├─ __init__.py
├─ layout_models.py
├─ base_layout_analyzer.py
├─ pypdf_layout_analyzer.py
├─ docling_layout_analyzer.py
├─ dolphin_layout_analyzer.py
└─ main_analyze_layout.py
```

Recommended development order:

```text
1. Define shared layout output models.
2. Implement a lightweight pypdf-based baseline analyzer.
3. Use the baseline analyzer to generate layout_blocks.json.
4. Later add Docling or Dolphin adapters if needed.
```

## Why Adapter-Based Instead of One Fixed Tool

Different document parsing tools have different strengths.

A lightweight baseline based on existing text extraction is easy to run and debug. More advanced tools can provide better table, figure, and layout understanding, but may require heavier dependencies or model setup.

Therefore, the repo should not hard-code one parser as the only option.

Instead, the layout layer should expose a common output schema:

```text
PDF
    ↓
layout analyzer backend
    ↓
layout_blocks.json
```

Possible future backend options:

```text
pypdf baseline
Docling parser
Dolphin parser
MinerU parser
other OCR/layout models
```

The first implementation can use the pypdf baseline. This keeps the pipeline runnable while leaving room for stronger backends later.

## Planned Output

The layout analysis step should write:

```text
outputs/intermediate/layout_blocks.json
```

This file should contain layout-aware blocks that can later be selected and passed to the LLM.

## Proposed layout_blocks.json Structure

Example:

```json
{
  "source_file": "data/raw/vishay_temt6000x01_datasheet.pdf",
  "layout_backend": "pypdf_baseline",
  "page_count": 6,
  "blocks": [
    {
      "block_id": "page_1_block_001",
      "page_number": 1,
      "block_index": 1,
      "block_type": "section",
      "text": "DESCRIPTION\nTEMT6000X01 ambient light sensor is a silicon NPN...",
      "char_count": 120,
      "reading_order": 1,
      "section_heading": "DESCRIPTION",
      "bbox": null,
      "metadata": {
        "source": "pypdf_baseline",
        "confidence": null
      }
    }
  ]
}
```

## Minimal Block Fields

Each layout block should include:

```text
block_id
page_number
block_index
block_type
text
char_count
reading_order
section_heading
bbox
metadata
```

### block_id

A stable local identifier for the block.

Example:

```text
page_1_block_001
```

### page_number

One-based page number matching the original PDF.

### block_index

Index of the block within the page.

### block_type

A coarse block type.

Recommended initial values:

```text
title
heading
paragraph
list
table_like
figure_caption
figure_or_graph
package_drawing
boilerplate
legal
unknown
```

The first baseline implementation may use simple heuristics to assign these types.

### text

The raw text content of the block.

This should not be aggressively normalized. Later evidence extraction needs access to the original local wording.

### char_count

Number of characters in the block text.

### reading_order

Order of the block in the page.

For the pypdf baseline, reading order can initially follow text order.

### section_heading

The nearest detected section heading if available.

Example:

```text
BASIC CHARACTERISTICS
ABSOLUTE MAXIMUM RATINGS
PACKAGE DIMENSIONS
```

If no heading is detected, this field can be null.

### bbox

Optional bounding box information.

For the pypdf baseline, this can be null.

For future layout backends, this can store:

```json
{
  "x0": 0.0,
  "y0": 0.0,
  "x1": 100.0,
  "y1": 50.0
}
```

### metadata

Backend-specific metadata.

Example:

```json
{
  "source": "pypdf_baseline",
  "confidence": null
}
```

## First Baseline Implementation

The first layout analyzer does not need a heavy layout model.

It can use the existing page-level text and split pages into coarse blocks based on:

- known section headings;
- blank lines;
- table heading patterns;
- legal disclaimer markers;
- packaging-only markers;
- figure markers such as `Fig.`;
- package dimension markers.

Example heuristic rules:

```text
line starts with known heading → heading / section split
contains PARAMETER + SYMBOL + UNIT → table_like
starts with Fig. → figure_caption or figure_or_graph
contains Legal Disclaimer → legal
contains BLISTER TAPE or REEL DIMENSIONS → packaging / boilerplate
```

This baseline is not meant to be perfect. It is meant to establish the intermediate representation and keep the pipeline runnable.

## Relation to Page Scoring

Page scoring currently works at page level.

After layout analysis is added, scoring can be improved in two ways:

```text
current:
    page_texts.json → page scoring

future:
    page_texts.json + layout_blocks.json → layout-aware page scoring
```

For example, a page with a legal footer should not be heavily penalized if the main content blocks are technical. A layout-aware scorer can distinguish:

```text
technical table block
legal boilerplate footer
```

instead of treating the whole page as one flat text.

## Relation to Content Block Building

The content block builder should eventually use:

```text
selected_pages.json
layout_blocks.json
```

to produce:

```text
selected_content_blocks.json
```

The selected content blocks should contain only the useful blocks from selected pages, not necessarily the full page text.

For the first implementation, it is acceptable to produce full-page blocks. After layout analysis is implemented, the builder should prefer layout blocks.

## Proposed selected_content_blocks.json Structure

Example:

```json
{
  "source_file": "data/raw/vishay_temt6000x01_datasheet.pdf",
  "selection_strategy": "hybrid",
  "content_block_source": "layout_blocks",
  "blocks": [
    {
      "content_block_id": "content_page_2_block_003",
      "source_block_id": "page_2_block_003",
      "page_number": 2,
      "block_type": "table_like",
      "section_heading": "BASIC CHARACTERISTICS",
      "text": "PARAMETER TEST CONDITION SYMBOL MIN. TYP. MAX. UNIT...",
      "selection_status": "selected_primary",
      "rule_based_score": 71.5,
      "llm_score": 90.0,
      "llm_likely_content_type": "technical parameters"
    }
  ]
}
```

## Relation to LangChain Extraction

LangChain extraction should not receive the whole PDF.

It should receive:

```text
selected_content_blocks.json
target graph vocabulary
allowed parameter types
allowed unit vocabulary
expected structured output schema
```

The LLM should extract only graph-supported target information.

The LLM should not normalize units and should not convert units.

The LLM should output raw, evidence-rich extraction objects.

## Evidence Requirements

Layout analysis supports evidence grounding.

Each extracted parameter should later be traceable to:

```text
source_file
page_number
source_block_id
source_text
```

This is why layout blocks need stable block IDs.

Evidence should remain valid even after unit normalization and graph-shaped JSON conversion.

## Avoiding Semantic Loss

The pipeline should avoid semantic loss across two transformations:

```text
layout-aware content blocks
    ↓
raw structured extraction result
    ↓
graph-shaped JSON
```

To reduce semantic loss, the raw extraction result should keep:

```text
raw_label
raw_value
raw_unit
raw_text_span
source_page
source_block_id
source_text
confidence
extraction_status
uncertainty_note
```

The graph-shaped JSON conversion should preserve raw fields and add normalized fields instead of replacing them.

Recommended principle:

```text
Preserve raw semantics first.
Normalize and map only as an additional layer.
```

## Unit Normalization Boundary

The LLM should not perform unit normalization.

The LLM may extract:

```text
raw_unit: "°"
raw_unit: "deg"
raw_unit: "μA"
raw_unit: "µA"
```

Python should normalize and validate units against the graph vocabulary.

Example:

```text
raw unit "°"  → normalized unit "deg"
raw unit "µA" → normalized unit "μA"
```

If a unit cannot be normalized, the result should be flagged instead of silently corrected.

## Missing Information

Missing information is allowed.

The extraction model may explicitly represent missing targets, for example:

```json
{
  "parameter_type": "Forward Voltage",
  "extraction_status": "not_found",
  "reason": "No explicit value found in selected content blocks."
}
```

Only found parameters should be converted into `TechnicalParameter` nodes.

Missing targets can be reported separately or checked later through CQ validation.

## Success Criteria

The layout analysis layer can be considered complete when:

```text
1. A layout analyzer can read page_texts.json or a PDF input.
2. It writes layout_blocks.json.
3. Each block has a stable block_id.
4. Each block preserves page number and reading order.
5. Blocks have coarse block types.
6. Blocks preserve enough raw text for evidence grounding.
7. selected_content_blocks.json can be built from selected pages and layout blocks.
8. LangChain extraction can use selected content blocks instead of full PDF text.
```

## Current Recommended Next Step

Implement the shared layout model and a lightweight baseline analyzer first:

```text
src/graph_datasheet_extractor/layout_analysis/layout_models.py
src/graph_datasheet_extractor/layout_analysis/pypdf_layout_analyzer.py
src/graph_datasheet_extractor/layout_analysis/main_analyze_layout.py
```

After this baseline is stable, optional advanced backends can be added without changing downstream components.
