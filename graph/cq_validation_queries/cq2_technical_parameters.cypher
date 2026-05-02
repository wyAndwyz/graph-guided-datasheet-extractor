// -----------------------------------------------------------------------------
// CQ2: Which technical parameters were extracted for each equipment?
//
// Purpose:
// List all extracted technical parameters for each equipment.
// Show both the raw extracted label/value and the normalized ParameterType / Unit.
// -----------------------------------------------------------------------------

MATCH (e:Equipment)-[:HAS_PARAMETER]->(p:TechnicalParameter)
MATCH (p)-[:HAS_PARAMETER_TYPE]->(pt:ParameterType)
OPTIONAL MATCH (p)-[:HAS_UNIT]->(u:Unit)
RETURN
  e.id AS equipment_id,
  e.product_model AS product_model,
  e.raw_equipment_type AS raw_equipment_type,
  p.id AS parameter_id,
  p.raw_label AS raw_label,
  p.value AS value,
  p.value_type AS value_type,
  pt.name AS normalized_parameter_type,
  pt.display_name AS parameter_display_name,
  pt.parameter_category AS parameter_category,
  u.symbol AS unit,
  u.name AS unit_name
ORDER BY equipment_id, normalized_parameter_type, raw_label;