// -----------------------------------------------------------------------------
// CQ1: Which equipment was extracted from the datasheet?
//
// Purpose:
// List equipment instances extracted from each datasheet.
// If available, also show the normalized equipment type from the vocabulary graph.
// -----------------------------------------------------------------------------

MATCH (d:Datasheet)-[:DESCRIBES]->(e:Equipment)
OPTIONAL MATCH (e)-[:HAS_EQUIPMENT_TYPE]->(et:EquipmentType)
RETURN
  d.id AS datasheet_id,
  d.file_name AS file_name,
  d.document_type AS document_type,
  e.id AS equipment_id,
  e.product_model AS product_model,
  e.manufacturer AS manufacturer,
  e.raw_equipment_type AS raw_equipment_type,
  et.name AS normalized_equipment_type,
  et.display_name AS normalized_equipment_type_display_name
ORDER BY datasheet_id, equipment_id;