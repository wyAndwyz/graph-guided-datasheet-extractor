// -----------------------------------------------------------------------------
// 05_unit_vocabulary.cypher
//
// Purpose:
// Initialize the unit vocabulary for the MVP and variation datasheets.
//
// The Unit vocabulary is used for:
// - graph-guided document screening;
// - graph-guided prompt construction;
// - vocabulary grounding;
// - unit validation;
// - Cypher-based validation.
// -----------------------------------------------------------------------------

// -----------------------------------------------------------------------------
// MVP unit vocabulary for Vishay TEMT6000X01
// -----------------------------------------------------------------------------

MERGE (u:Unit {symbol: "mm"})
SET
  u.name = "millimetre",
  u.dimension = "length",
  u.scope = "mvp",
  u.description = "Millimetre, used for physical dimensions.";

MERGE (u:Unit {symbol: "nm"})
SET
  u.name = "nanometre",
  u.dimension = "length",
  u.scope = "mvp",
  u.description = "Nanometre, used for optical wavelength.";

MERGE (u:Unit {symbol: "degree"})
SET
  u.name = "degree",
  u.dimension = "angle",
  u.scope = "mvp",
  u.description = "Degree, used for angular values such as half-sensitivity angle.";


// -----------------------------------------------------------------------------
// Variation unit vocabulary for Analog Devices ADXL345
// These units are included early for later extension, but are not required
// by the primary MVP datasheet.
// -----------------------------------------------------------------------------

MERGE (u:Unit {symbol: "g"})
SET
  u.name = "standard gravity",
  u.dimension = "acceleration",
  u.scope = "variation",
  u.description = "Unit used for acceleration measurement range.";

MERGE (u:Unit {symbol: "bit"})
SET
  u.name = "bit",
  u.dimension = "digital_resolution",
  u.scope = "variation",
  u.description = "Unit used for digital resolution.";

MERGE (u:Unit {symbol: "V"})
SET
  u.name = "volt",
  u.dimension = "voltage",
  u.scope = "variation",
  u.description = "Volt, used for supply voltage.";

MERGE (u:Unit {symbol: "µA"})
SET
  u.name = "microampere",
  u.dimension = "electric_current",
  u.scope = "variation",
  u.description = "Microampere, used for current consumption.";

MERGE (u:Unit {symbol: "°C"})
SET
  u.name = "degree Celsius",
  u.dimension = "temperature",
  u.scope = "variation",
  u.description = "Degree Celsius, used for operating temperature range.";


// -----------------------------------------------------------------------------
// Connect Unit vocabulary entries to the Unit concept
// -----------------------------------------------------------------------------

MATCH (unitConcept:Concept {name: "Unit"})
MATCH (u:Unit {symbol: "mm"})
MERGE (u)-[:INSTANCE_OF_CONCEPT]->(unitConcept);

MATCH (unitConcept:Concept {name: "Unit"})
MATCH (u:Unit {symbol: "nm"})
MERGE (u)-[:INSTANCE_OF_CONCEPT]->(unitConcept);

MATCH (unitConcept:Concept {name: "Unit"})
MATCH (u:Unit {symbol: "degree"})
MERGE (u)-[:INSTANCE_OF_CONCEPT]->(unitConcept);

MATCH (unitConcept:Concept {name: "Unit"})
MATCH (u:Unit {symbol: "g"})
MERGE (u)-[:INSTANCE_OF_CONCEPT]->(unitConcept);

MATCH (unitConcept:Concept {name: "Unit"})
MATCH (u:Unit {symbol: "bit"})
MERGE (u)-[:INSTANCE_OF_CONCEPT]->(unitConcept);

MATCH (unitConcept:Concept {name: "Unit"})
MATCH (u:Unit {symbol: "V"})
MERGE (u)-[:INSTANCE_OF_CONCEPT]->(unitConcept);

MATCH (unitConcept:Concept {name: "Unit"})
MATCH (u:Unit {symbol: "µA"})
MERGE (u)-[:INSTANCE_OF_CONCEPT]->(unitConcept);

MATCH (unitConcept:Concept {name: "Unit"})
MATCH (u:Unit {symbol: "°C"})
MERGE (u)-[:INSTANCE_OF_CONCEPT]->(unitConcept);


// -----------------------------------------------------------------------------
// Allowed units for MVP parameter types
// -----------------------------------------------------------------------------

MATCH (pt:ParameterType {name: "Dimensions"})
MATCH (u:Unit {symbol: "mm"})
MERGE (pt)-[:ALLOWS_UNIT]->(u);

MATCH (pt:ParameterType {name: "PeakSensitivityWavelength"})
MATCH (u:Unit {symbol: "nm"})
MERGE (pt)-[:ALLOWS_UNIT]->(u);

MATCH (pt:ParameterType {name: "AngleOfHalfSensitivity"})
MATCH (u:Unit {symbol: "degree"})
MERGE (pt)-[:ALLOWS_UNIT]->(u);


// -----------------------------------------------------------------------------
// Optional string-like parameter types without physical units
//
// These parameters are intentionally not connected to a Unit node:
// - Manufacturer
// - ProductModel
// - DeviceType
// - PackageType
// - PackageForm
//
// They are string-valued or categorical parameters.
// -----------------------------------------------------------------------------
