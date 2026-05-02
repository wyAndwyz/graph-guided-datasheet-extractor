// -----------------------------------------------------------------------------
// CQ5: Which required parameters are missing or use unsupported units?
//
// Purpose:
// Check whether each Equipment has all RequiredParameter types and whether
// extracted units are supported by the corresponding ParameterType vocabulary.
// -----------------------------------------------------------------------------

// Case 1: Missing required parameters
MATCH (e:Equipment)
MATCH (rp:RequiredParameter)-[:REQUIRES_PARAMETER_TYPE]->(required_pt:ParameterType)
WHERE NOT EXISTS {
  MATCH (e)-[:HAS_PARAMETER]->(:TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(required_pt)
}
RETURN
  e.id AS equipment_id,
  e.product_model AS product_model,
  "MISSING_REQUIRED_PARAMETER" AS issue_type,
  required_pt.name AS parameter_type,
  null AS raw_label,
  null AS value,
  null AS unit,
  rp.reason AS detail

UNION

// Case 2: Parameter has a unit, but the unit is not allowed by its ParameterType
MATCH (e:Equipment)-[:HAS_PARAMETER]->(p:TechnicalParameter)
MATCH (p)-[:HAS_PARAMETER_TYPE]->(pt:ParameterType)
MATCH (p)-[:HAS_UNIT]->(u:Unit)
WHERE NOT EXISTS {
  MATCH (pt)-[:ALLOWS_UNIT]->(u)
}
RETURN
  e.id AS equipment_id,
  e.product_model AS product_model,
  "UNSUPPORTED_UNIT" AS issue_type,
  pt.name AS parameter_type,
  p.raw_label AS raw_label,
  p.value AS value,
  u.symbol AS unit,
  "The extracted unit is not listed as an allowed unit for this ParameterType." AS detail

UNION

// Case 3: ParameterType expects a unit, but the extracted parameter has no Unit
MATCH (e:Equipment)-[:HAS_PARAMETER]->(p:TechnicalParameter)
MATCH (p)-[:HAS_PARAMETER_TYPE]->(pt:ParameterType)
WHERE pt.expects_unit = true
  AND NOT EXISTS {
    MATCH (p)-[:HAS_UNIT]->(:Unit)
  }
RETURN
  e.id AS equipment_id,
  e.product_model AS product_model,
  "MISSING_EXPECTED_UNIT" AS issue_type,
  pt.name AS parameter_type,
  p.raw_label AS raw_label,
  p.value AS value,
  null AS unit,
  "This ParameterType expects a unit, but the extracted parameter has no HAS_UNIT relationship." AS detail

ORDER BY equipment_id, issue_type, parameter_type;