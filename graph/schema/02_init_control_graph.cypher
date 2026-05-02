// -----------------------------------------------------------------------------
// 02_init_control_graph.cypher
//
// Purpose:
// Initialize the lightweight control/vocabulary graph for the MVP.
//
// The control graph is used to guide:
// - document screening before LLM calls;
// - graph-guided prompt construction;
// - structured extraction targets;
// - vocabulary grounding;
// - Cypher-based validation.
// -----------------------------------------------------------------------------

// -----------------------------------------------------------------------------
// Core concepts
// -----------------------------------------------------------------------------

MERGE (c:Concept {name: "Datasheet"})
SET
  c.description = "A technical datasheet document used as input for extraction.",
  c.category = "instance_label";

MERGE (c:Concept {name: "Equipment"})
SET
  c.description = "A product or device described by a datasheet.",
  c.category = "instance_label";

MERGE (c:Concept {name: "TechnicalParameter"})
SET
  c.description = "An extracted technical parameter value from a datasheet.",
  c.category = "instance_label";

MERGE (c:Concept {name: "ParameterType"})
SET
  c.description = "A normalized vocabulary concept describing the semantic type of a technical parameter.",
  c.category = "vocabulary_label";

MERGE (c:Concept {name: "Unit"})
SET
  c.description = "A normalized unit vocabulary concept.",
  c.category = "vocabulary_label";

MERGE (c:Concept {name: "Evidence"})
SET
  c.description = "Source evidence supporting an extracted technical parameter.",
  c.category = "instance_label";

MERGE (c:Concept {name: "ExtractionRun"})
SET
  c.description = "A record of one extraction run.",
  c.category = "instance_label";

MERGE (c:Concept {name: "ValidationIssue"})
SET
  c.description = "A validation issue detected after extraction or graph population.",
  c.category = "instance_label";


// -----------------------------------------------------------------------------
// Relationship definitions
// -----------------------------------------------------------------------------

MERGE (rd:RelationshipDefinition {name: "DESCRIBES"})
SET rd.description = "Links a datasheet to the equipment described by it.";

MERGE (rd:RelationshipDefinition {name: "HAS_PARAMETER"})
SET rd.description = "Links equipment to an extracted technical parameter.";

MERGE (rd:RelationshipDefinition {name: "HAS_PARAMETER_TYPE"})
SET rd.description = "Links an extracted technical parameter to its normalized parameter type.";

MERGE (rd:RelationshipDefinition {name: "HAS_UNIT"})
SET rd.description = "Links an extracted technical parameter to its normalized unit.";

MERGE (rd:RelationshipDefinition {name: "EVIDENCED_BY"})
SET rd.description = "Links an extracted technical parameter to its supporting source evidence.";

MERGE (rd:RelationshipDefinition {name: "GENERATED_BY"})
SET rd.description = "Links an extracted technical parameter to the extraction run that generated it.";

MERGE (rd:RelationshipDefinition {name: "ABOUT"})
SET rd.description = "Links a validation issue to the graph element it concerns.";


// -----------------------------------------------------------------------------
// Relationship definition domains and ranges
// -----------------------------------------------------------------------------

MATCH (fromConcept:Concept {name: "Datasheet"})
MATCH (toConcept:Concept {name: "Equipment"})
MATCH (rd:RelationshipDefinition {name: "DESCRIBES"})
MERGE (rd)-[:FROM_CONCEPT]->(fromConcept)
MERGE (rd)-[:TO_CONCEPT]->(toConcept);

MATCH (fromConcept:Concept {name: "Equipment"})
MATCH (toConcept:Concept {name: "TechnicalParameter"})
MATCH (rd:RelationshipDefinition {name: "HAS_PARAMETER"})
MERGE (rd)-[:FROM_CONCEPT]->(fromConcept)
MERGE (rd)-[:TO_CONCEPT]->(toConcept);

MATCH (fromConcept:Concept {name: "TechnicalParameter"})
MATCH (toConcept:Concept {name: "ParameterType"})
MATCH (rd:RelationshipDefinition {name: "HAS_PARAMETER_TYPE"})
MERGE (rd)-[:FROM_CONCEPT]->(fromConcept)
MERGE (rd)-[:TO_CONCEPT]->(toConcept);

MATCH (fromConcept:Concept {name: "TechnicalParameter"})
MATCH (toConcept:Concept {name: "Unit"})
MATCH (rd:RelationshipDefinition {name: "HAS_UNIT"})
MERGE (rd)-[:FROM_CONCEPT]->(fromConcept)
MERGE (rd)-[:TO_CONCEPT]->(toConcept);

MATCH (fromConcept:Concept {name: "TechnicalParameter"})
MATCH (toConcept:Concept {name: "Evidence"})
MATCH (rd:RelationshipDefinition {name: "EVIDENCED_BY"})
MERGE (rd)-[:FROM_CONCEPT]->(fromConcept)
MERGE (rd)-[:TO_CONCEPT]->(toConcept);

MATCH (fromConcept:Concept {name: "TechnicalParameter"})
MATCH (toConcept:Concept {name: "ExtractionRun"})
MATCH (rd:RelationshipDefinition {name: "GENERATED_BY"})
MERGE (rd)-[:FROM_CONCEPT]->(fromConcept)
MERGE (rd)-[:TO_CONCEPT]->(toConcept);

MATCH (fromConcept:Concept {name: "ValidationIssue"})
MATCH (toConcept:Concept {name: "TechnicalParameter"})
MATCH (rd:RelationshipDefinition {name: "ABOUT"})
MERGE (rd)-[:FROM_CONCEPT]->(fromConcept)
MERGE (rd)-[:TO_CONCEPT]->(toConcept);


// -----------------------------------------------------------------------------
// MVP parameter type vocabulary for Vishay TEMT6000X01
// -----------------------------------------------------------------------------

MERGE (pt:ParameterType {name: "Manufacturer"})
SET
  pt.description = "The manufacturer of the device.",
  pt.value_type = "string",
  pt.priority = "optional";

MERGE (pt:ParameterType {name: "ProductModel"})
SET
  pt.description = "The product model or part number.",
  pt.value_type = "string",
  pt.priority = "required";

MERGE (pt:ParameterType {name: "DeviceType"})
SET
  pt.description = "The general device type described by the datasheet.",
  pt.value_type = "string",
  pt.priority = "required";

MERGE (pt:ParameterType {name: "PackageType"})
SET
  pt.description = "The package or mounting type of the device.",
  pt.value_type = "string",
  pt.priority = "optional";

MERGE (pt:ParameterType {name: "PackageForm"})
SET
  pt.description = "The specific package form or package code, such as 1206.",
  pt.value_type = "string",
  pt.priority = "required";

MERGE (pt:ParameterType {name: "Dimensions"})
SET
  pt.description = "Physical dimensions of the device.",
  pt.value_type = "string_or_dimension_tuple",
  pt.priority = "required";

MERGE (pt:ParameterType {name: "PeakSensitivityWavelength"})
SET
  pt.description = "The wavelength at which the sensor has peak sensitivity.",
  pt.value_type = "number",
  pt.priority = "required";

MERGE (pt:ParameterType {name: "AngleOfHalfSensitivity"})
SET
  pt.description = "The angle at which sensor sensitivity drops to half of its maximum.",
  pt.value_type = "number_or_range",
  pt.priority = "optional";


// -----------------------------------------------------------------------------
// Connect parameter types to the ParameterType concept
// -----------------------------------------------------------------------------

MATCH (parameterTypeConcept:Concept {name: "ParameterType"})
MATCH (pt:ParameterType {name: "Manufacturer"})
MERGE (pt)-[:INSTANCE_OF_CONCEPT]->(parameterTypeConcept);

MATCH (parameterTypeConcept:Concept {name: "ParameterType"})
MATCH (pt:ParameterType {name: "ProductModel"})
MERGE (pt)-[:INSTANCE_OF_CONCEPT]->(parameterTypeConcept);

MATCH (parameterTypeConcept:Concept {name: "ParameterType"})
MATCH (pt:ParameterType {name: "DeviceType"})
MERGE (pt)-[:INSTANCE_OF_CONCEPT]->(parameterTypeConcept);

MATCH (parameterTypeConcept:Concept {name: "ParameterType"})
MATCH (pt:ParameterType {name: "PackageType"})
MERGE (pt)-[:INSTANCE_OF_CONCEPT]->(parameterTypeConcept);

MATCH (parameterTypeConcept:Concept {name: "ParameterType"})
MATCH (pt:ParameterType {name: "PackageForm"})
MERGE (pt)-[:INSTANCE_OF_CONCEPT]->(parameterTypeConcept);

MATCH (parameterTypeConcept:Concept {name: "ParameterType"})
MATCH (pt:ParameterType {name: "Dimensions"})
MERGE (pt)-[:INSTANCE_OF_CONCEPT]->(parameterTypeConcept);

MATCH (parameterTypeConcept:Concept {name: "ParameterType"})
MATCH (pt:ParameterType {name: "PeakSensitivityWavelength"})
MERGE (pt)-[:INSTANCE_OF_CONCEPT]->(parameterTypeConcept);

MATCH (parameterTypeConcept:Concept {name: "ParameterType"})
MATCH (pt:ParameterType {name: "AngleOfHalfSensitivity"})
MERGE (pt)-[:INSTANCE_OF_CONCEPT]->(parameterTypeConcept);


// -----------------------------------------------------------------------------
// Required parameters for the MVP
// -----------------------------------------------------------------------------

MERGE (rp:RequiredParameter {id: "required_product_model"})
SET rp.reason = "The product model identifies the device described by the datasheet.";

MERGE (rp:RequiredParameter {id: "required_device_type"})
SET rp.reason = "The device type is required for classifying the extracted equipment.";

MERGE (rp:RequiredParameter {id: "required_package_form"})
SET rp.reason = "The package form is a core device specification for the MVP datasheet.";

MERGE (rp:RequiredParameter {id: "required_dimensions"})
SET rp.reason = "Physical dimensions are a core technical parameter for the MVP datasheet.";

MERGE (rp:RequiredParameter {id: "required_peak_sensitivity_wavelength"})
SET rp.reason = "Peak sensitivity wavelength is a characteristic optical parameter of the ambient light sensor.";


// -----------------------------------------------------------------------------
// Connect required parameters to parameter types
// -----------------------------------------------------------------------------

MATCH (rp:RequiredParameter {id: "required_product_model"})
MATCH (pt:ParameterType {name: "ProductModel"})
MERGE (rp)-[:REQUIRES_PARAMETER_TYPE]->(pt);

MATCH (rp:RequiredParameter {id: "required_device_type"})
MATCH (pt:ParameterType {name: "DeviceType"})
MERGE (rp)-[:REQUIRES_PARAMETER_TYPE]->(pt);

MATCH (rp:RequiredParameter {id: "required_package_form"})
MATCH (pt:ParameterType {name: "PackageForm"})
MERGE (rp)-[:REQUIRES_PARAMETER_TYPE]->(pt);

MATCH (rp:RequiredParameter {id: "required_dimensions"})
MATCH (pt:ParameterType {name: "Dimensions"})
MERGE (rp)-[:REQUIRES_PARAMETER_TYPE]->(pt);

MATCH (rp:RequiredParameter {id: "required_peak_sensitivity_wavelength"})
MATCH (pt:ParameterType {name: "PeakSensitivityWavelength"})
MERGE (rp)-[:REQUIRES_PARAMETER_TYPE]->(pt);