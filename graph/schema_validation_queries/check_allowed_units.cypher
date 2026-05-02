MATCH (pt:ParameterType)-[:ALLOWS_UNIT]->(u:Unit)
WITH pt.name AS parameter_type, u.symbol AS unit
ORDER BY parameter_type, unit
WITH parameter_type, collect(unit) AS allowed_units
RETURN parameter_type, allowed_units
ORDER BY parameter_type;