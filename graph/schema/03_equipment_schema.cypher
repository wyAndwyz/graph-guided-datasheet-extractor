// -----------------------------------------------------------------------------
// 03_equipment_schema.cypher
//
// Purpose:
// Initialize lightweight equipment-related vocabulary for the MVP and variation
// datasheets.
//
// This file defines EquipmentType vocabulary entries used for:
// - document screening;
// - graph-guided prompt construction;
// - equipment type grounding;
// - validation and query-based inspection.
// -----------------------------------------------------------------------------

// -----------------------------------------------------------------------------
// Optional relationship definition for equipment type grounding
// -----------------------------------------------------------------------------

MERGE (rd:RelationshipDefinition {name: "HAS_EQUIPMENT_TYPE"})
SET rd.description = "Links extracted equipment to its normalized equipment type.";

MATCH (fromConcept:Concept {name: "Equipment"})
MATCH (toConcept:Concept {name: "Equipment"})
MATCH (rd:RelationshipDefinition {name: "HAS_EQUIPMENT_TYPE"})
MERGE (rd)-[:FROM_CONCEPT]->(fromConcept)
MERGE (rd)-[:TO_CONCEPT]->(toConcept);


// -----------------------------------------------------------------------------
// Equipment type vocabulary
// -----------------------------------------------------------------------------

MERGE (et:EquipmentType {name: "AmbientLightSensor"})
SET
  et.display_name = "Ambient light sensor",
  et.description = "A sensor device that detects ambient light intensity.",
  et.scope = "mvp",
  et.source_product = "Vishay TEMT6000X01";

MERGE (et:EquipmentType {name: "DigitalAccelerometer"})
SET
  et.display_name = "Digital accelerometer",
  et.description = "A sensor device that measures acceleration and provides digital output.",
  et.scope = "variation",
  et.source_product = "Analog Devices ADXL345";


// -----------------------------------------------------------------------------
// Connect equipment types to the Equipment concept
// -----------------------------------------------------------------------------

MATCH (equipmentConcept:Concept {name: "Equipment"})
MATCH (et:EquipmentType {name: "AmbientLightSensor"})
MERGE (et)-[:INSTANCE_OF_CONCEPT]->(equipmentConcept);

MATCH (equipmentConcept:Concept {name: "Equipment"})
MATCH (et:EquipmentType {name: "DigitalAccelerometer"})
MERGE (et)-[:INSTANCE_OF_CONCEPT]->(equipmentConcept);


// -----------------------------------------------------------------------------
// Candidate aliases for equipment type grounding
//
// These aliases are used later by document screening, prompt construction,
// and vocabulary matching. They are stored as properties for simplicity in the
// MVP version.
// -----------------------------------------------------------------------------

MATCH (et:EquipmentType {name: "AmbientLightSensor"})
SET et.aliases = [
  "ambient light sensor",
  "ambient light sensors",
  "light sensor",
  "photo sensor",
  "photosensor"
];

MATCH (et:EquipmentType {name: "DigitalAccelerometer"})
SET et.aliases = [
  "accelerometer",
  "digital accelerometer",
  "3-axis accelerometer",
  "three-axis accelerometer",
  "3-axis digital accelerometer"
];