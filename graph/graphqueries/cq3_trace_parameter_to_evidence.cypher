// -----------------------------------------------------------------------------
// CQ3: Which source evidence supports each extracted parameter,
//      and what is the evidence status?
//
// Purpose:
// Trace each extracted technical parameter back to its source evidence.
// This supports evidence-grounded extraction and hallucination-risk inspection.
// -----------------------------------------------------------------------------

MATCH (e:Equipment)-[:HAS_PARAMETER]->(p:TechnicalParameter)
MATCH (p)-[:HAS_PARAMETER_TYPE]->(pt:ParameterType)
OPTIONAL MATCH (p)-[:HAS_UNIT]->(u:Unit)
OPTIONAL MATCH (p)-[:EVIDENCED_BY]->(ev:Evidence)
RETURN
  e.id AS equipment_id,
  e.product_model AS product_model,
  p.id AS parameter_id,
  p.raw_label AS raw_label,
  p.value AS value,
  pt.name AS normalized_parameter_type,
  u.symbol AS unit,
  ev.id AS evidence_id,
  ev.page_number AS page_number,
  ev.content_block_id AS content_block_id,
  ev.source_text AS source_text,
  ev.evidence_type AS evidence_type,
  ev.evidence_status AS evidence_status,
  ev.confidence AS confidence,
  ev.extraction_method AS extraction_method
ORDER BY equipment_id, normalized_parameter_type, confidence DESC;