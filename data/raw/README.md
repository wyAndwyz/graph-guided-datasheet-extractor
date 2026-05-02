# Raw Datasheets

This folder contains locally downloaded public datasheet PDFs used as input for the graph-guided extraction pipeline.

The files in this folder are treated as raw input documents and should not be manually modified.

## Purpose

Raw datasheets are used for:

- PDF loading;
- page-level text extraction;
- graph-guided page screening;
- selected content block construction;
- later LangChain-based structured extraction;
- evidence-grounded graph population.

The pipeline should not send the entire datasheet to the LLM by default. Instead, it should first perform local page/content screening and only pass selected relevant content blocks to the LLM.

## Current Datasheets

### 1. Vishay TEMT6000X01

- Company: Vishay Semiconductors
- Product: TEMT6000X01
- Device type: Ambient light sensor
- Official product page: https://www.vishay.com/en/product/81579/
- Official datasheet PDF: https://www.vishay.com/docs/81579/temt6000.pdf
- Recommended local filename: `vishay_temt6000x01_datasheet.pdf`

This datasheet is the primary MVP datasheet.

### 2. Analog Devices ADXL345

- Company: Analog Devices
- Product: ADXL345
- Device type: 3-axis digital accelerometer
- Official product page: https://www.analog.com/en/products/adxl345.html
- Official datasheet PDF: https://www.analog.com/media/en/technical-documentation/data-sheets/adxl345.pdf
- Recommended local filename: `analog_devices_adxl345_datasheet.pdf`

This datasheet is the variation case for later testing.

## Download Instructions

Download the PDF files from the official vendor links above and save them in this folder using the recommended filenames.

Expected local structure:

```text
data/raw/
├─ README.md
├─ vishay_temt6000x01_datasheet.pdf
└─ analog_devices_adxl345_datasheet.pdf
```

## Git Policy

By default, PDF files in this folder should not be committed to Git.

Recommended .gitignore entries:
```
data/raw/*.pdf
data/raw/*.PDF
```
The repository documents where to download the datasheets, but should normally avoid redistributing third-party PDF files directly.