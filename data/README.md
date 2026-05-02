# Data Folder

This folder contains input files, sample files, and reference outputs used by the graph-guided datasheet extraction demo.

The project separates raw datasheets, shareable sample data, and manually prepared reference outputs.

## Folder Structure

```text
data/
├─ README.md
├─ raw/
│  ├─ README.md
│  ├─ vishay_temt6000x01_datasheet.pdf
│  └─ analog_devices_adxl345_datasheet.pdf
│
├─ sample/
│  └─ README.md
│
└─ gold/
   ├─ sample_graph_extraction.json
   └─ sample_validation_expected.json
```

## Subfolders
### data/raw/

This folder contains locally downloaded public datasheet PDFs.

Raw PDF files are used as input for document ingestion, page-level text extraction, page screening, and later LLM-based extraction.

PDF files in this folder are ignored by Git by default to avoid committing third-party datasheets directly to the repository.

### data/sample/

This folder is reserved for small synthetic or shareable sample inputs.

Synthetic samples can be used when the repository should run without downloading third-party PDF files.

### data/gold/

This folder contains manually prepared reference outputs.

Gold files are used for testing the pipeline before LLM extraction is implemented.

Examples:

sample_graph_extraction.json: manually prepared graph-shaped extraction result.
sample_validation_expected.json: expected validation output.

## Data Handling Principle

The repository should only use public datasheets or synthetic examples.

The selected datasheets are documented in:

docs/datasheet_selection.md

## Git Tracking Policy

Recommended policy:

 - track README files and manually created small JSON examples;
 - do not track large or third-party PDF files by default;
 - store downloaded datasheets locally in data/raw/;
 - document official download links in docs/datasheet_selection.md and data/raw/README.md. 

The .gitignore file should normally include:
```
data/raw/*.pdf
data/raw/*.PDF
```
This keeps the repository lightweight and avoids redistributing third-party datasheets directly.