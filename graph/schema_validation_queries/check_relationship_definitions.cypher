MATCH (rd:RelationshipDefinition)-[:FROM_CONCEPT]->(from:Concept),
      (rd)-[:TO_CONCEPT]->(to:Concept)
RETURN
  rd.name AS relationship,
  from.name AS from_concept,
  to.name AS to_concept
ORDER BY relationship;