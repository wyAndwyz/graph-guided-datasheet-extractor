# Datasheet Selection

This document explains the datasheet selection strategy for the graph-guided datasheet extraction demo.

The repository is developed as a private job-search portfolio project. Therefore, the selected datasheets intentionally avoid process-industry-specific equipment and documents that are close to the author's current research and work context.

## Selection Rationale

This project focuses on a general graph-guided LLM information extraction workflow for public technical datasheets. To highlight the transferability of the approach, the initial demo uses electronic and sensor-device datasheets as a compact and publicly available application domain.

These datasheets provide structured technical information such as product identifiers, parameter tables, units, dimensions, and source evidence, while remaining sufficiently lightweight for a reproducible MVP.

## Datasheet Scope

The initial scope of this repository is limited to public electronic and sensor-device datasheets. This choice keeps the demo independent from ongoing research-specific datasets and allows the workflow to be presented as a general method for technical information extraction.

Other technical domains can be added later once the core pipeline for document screening, graph-guided extraction, Neo4j population, and validation is stable.

## Selected Datasheets

### Datasheet A — Primary MVP Datasheet

- Company: Vishay Semiconductors
- Product: TEMT6000X01
- Device type: Ambient light sensor
- Official product page: https://www.vishay.com/en/product/81579/
- Official datasheet PDF: https://www.vishay.com/docs/81579/temt6000.pdf
- Local filename: `vishay_temt6000x01_datasheet.pdf`

#### Reason for Selection

The TEMT6000X01 datasheet is suitable as the primary MVP datasheet because it is relatively short, public, and technically structured. It contains clear parameters such as package type, package form, dimensions, peak sensitivity, and angle of half sensitivity.

This makes it suitable for the first graph-shaped extraction workflow without overloading the initial implementation with a long or complex datasheet.

#### Candidate Parameters

The following parameters are suitable for the MVP extraction target:

- `EquipmentType`
- `Manufacturer`
- `ProductModel`
- `PackageType`
- `PackageForm`
- `Dimensions`
- `PeakSensitivity`
- `AngleOfHalfSensitivity`

#### Candidate Units

- `mm`
- `nm`
- `degree`

#### Intended Role in the Project

This datasheet is used for:

- first document screening test;
- first manually prepared sample graph extraction;
- first Neo4j graph population;
- first evidence-grounding demonstration;
- first vocabulary-grounding demonstration.

---

### Datasheet B — Variation Datasheet

- Company: Analog Devices
- Product: ADXL345
- Device type: 3-axis digital accelerometer
- Official product page: https://www.analog.com/en/products/adxl345.html
- Official datasheet PDF: https://www.analog.com/media/en/technical-documentation/data-sheets/adxl345.pdf
- Local filename: `analog_devices_adxl345_datasheet.pdf`

#### Reason for Selection

The ADXL345 datasheet is selected as a variation case. It is still outside the process-industry domain but introduces a more complex sensor datasheet with measurement range, resolution, digital interface, and supply-related parameters.

It is suitable for testing whether the graph-guided extraction workflow can generalize from a simple ambient light sensor datasheet to a more complex MEMS sensor datasheet.

#### Candidate Parameters

The following parameters are suitable for later extraction targets:

- `EquipmentType`
- `Manufacturer`
- `ProductModel`
- `MeasurementRange`
- `Resolution`
- `InterfaceType`
- `SupplyVoltage`
- `PackageType`
- `OperatingTemperatureRange`

#### Candidate Units

- `g`
- `bit`
- `V`
- `µA`
- `°C`

#### Intended Role in the Project

This datasheet is used for:

- later variation testing;
- parameter-type vocabulary expansion;
- unit vocabulary expansion;
- document screening evaluation on a longer datasheet;
- testing whether the pipeline remains reusable across different electronic sensor datasheets.

## Implementation Strategy

The MVP does not send entire datasheets to the LLM. Instead, the pipeline should perform local document screening before LLM extraction.

The intended workflow is:

```text
PDF datasheet
    ↓
local page-level text extraction
    ↓
graph-guided page/content screening
    ↓
selected content blocks
    ↓
LangChain structured extraction
    ↓
graph-shaped JSON
    ↓
Neo4j population and validation