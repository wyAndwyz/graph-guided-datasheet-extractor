MATCH (rp:RequiredParameter)-[:REQUIRES_PARAMETER_TYPE]->(pt:ParameterType)
RETURN
  rp.id AS required_parameter,
  pt.name AS parameter_type
ORDER BY required_parameter;