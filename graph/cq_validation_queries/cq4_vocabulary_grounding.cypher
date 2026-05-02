// -----------------------------------------------------------------------------
// CQ4: Which extracted parameters are normalized to known graph vocabulary concepts?
//
// Purpose:
// Check whether extracted parameters are grounded to ParameterType and,
// where applicable, Unit vocabulary nodes.
// -----------------------------------------------------------------------------

MATCH (e:Equipment)-[:HAS_PARAMETER]->(p:TechnicalParameter)
OPTIONAL MATCH (p)-[:HAS_PARAMETER_TYPE]->(pt:ParameterType)
OPTIONAL MATCH (p)-[:HAS_UNIT]->(u:Unit)
RETURN
  e.id AS equipment_id,
  e.product_model AS product_model,
  p.id AS parameter_id,
  p.raw_label AS raw_label,
  p.value AS value,
  pt.name AS grounded_parameter_type,
  pt.display_name AS parameter_display_name,
  CASE
    WHEN pt IS NOT NULL THEN "grounded"
    ELSE "not_grounded"
  END AS parameter_type_grounding_status,
  u.symbol AS grounded_unit,
  CASE
    WHEN u IS NOT NULL THEN "grounded"
    WHEN pt.expects_unit = true THEN "missing_unit_grounding"
    ELSE "not_required"
  END AS unit_grounding_status,
  pt.expects_unit AS parameter_type_expects_unit
ORDER BY equipment_id, parameter_type_grounding_status, unit_grounding_status, raw_label;