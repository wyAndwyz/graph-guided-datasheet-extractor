// -----------------------------------------------------------------------------
// 01_create_constraints.cypher
//
// Purpose:
// Create uniqueness constraints for the MVP Neo4j graph model.
//
// These constraints ensure that core nodes can be safely created or merged
// by their stable IDs or vocabulary keys during graph population.
// -----------------------------------------------------------------------------

// -----------------------------------------------------------------------------
// Instance graph constraints
// -----------------------------------------------------------------------------

CREATE CONSTRAINT datasheet_id_unique IF NOT EXISTS
FOR (d:Datasheet)
REQUIRE d.id IS UNIQUE;

//------------------------------------------------------------------------------
// Explanation:
//------------------------------------------------------------------------------
// CREATE CONSTRAINT: creates a database constraint.
// datasheet_id_unique: name of the constraint.
// IF NOT EXISTS: avoids error if the constraint already exists.
// FOR (d:Datasheet): applies the constraint to nodes with label Datasheet.
// REQUIRE d.id IS UNIQUE: requires the id property to be unique for all Datasheet nodes.
//------------------------------------------------------------------------------
// Purpose:
// This allows the graph loader to safely use MERGE (d:Datasheet {id: ...}).
// -----------------------------------------------------------------------------

CREATE CONSTRAINT equipment_id_unique IF NOT EXISTS
FOR (e:Equipment)
REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT technical_parameter_id_unique IF NOT EXISTS
FOR (p:TechnicalParameter)
REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS
FOR (ev:Evidence)
REQUIRE ev.id IS UNIQUE;

CREATE CONSTRAINT extraction_run_id_unique IF NOT EXISTS
FOR (r:ExtractionRun)
REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT validation_issue_id_unique IF NOT EXISTS
FOR (vi:ValidationIssue)
REQUIRE vi.id IS UNIQUE;


// -----------------------------------------------------------------------------
// Control / vocabulary graph constraints
// -----------------------------------------------------------------------------

CREATE CONSTRAINT concept_name_unique IF NOT EXISTS
FOR (c:Concept)
REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT parameter_type_name_unique IF NOT EXISTS
FOR (pt:ParameterType)
REQUIRE pt.name IS UNIQUE;

CREATE CONSTRAINT unit_symbol_unique IF NOT EXISTS
FOR (u:Unit)
REQUIRE u.symbol IS UNIQUE;

CREATE CONSTRAINT required_parameter_id_unique IF NOT EXISTS
FOR (rp:RequiredParameter)
REQUIRE rp.id IS UNIQUE;

CREATE CONSTRAINT allowed_unit_id_unique IF NOT EXISTS
FOR (au:AllowedUnit)
REQUIRE au.id IS UNIQUE;

CREATE CONSTRAINT relationship_definition_name_unique IF NOT EXISTS
FOR (rd:RelationshipDefinition)
REQUIRE rd.name IS UNIQUE;