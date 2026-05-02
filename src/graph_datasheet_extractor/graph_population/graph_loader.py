from __future__ import annotations

import os
import re
from typing import Any

from neo4j import GraphDatabase

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from graph_datasheet_extractor.graph_representation.graph_models import (
    GraphExtraction,
    GraphNode,
    GraphRelationship,
    TargetRef,
)


LABEL_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RELATIONSHIP_TYPE_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")
PROPERTY_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def get_neo4j_connection_config() -> dict[str, str]:
    """Load Neo4j connection settings from environment variables."""
    if load_dotenv is not None:
        load_dotenv()

    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "password"),
        "database": os.getenv("NEO4J_DATABASE", "neo4j"),
    }


def _validate_label(label: str) -> None:
    """Validate a Neo4j label before inserting it into a Cypher string."""
    if not LABEL_PATTERN.match(label):
        raise ValueError(f"Invalid Neo4j label: {label}")


def _validate_relationship_type(relationship_type: str) -> None:
    """Validate a Neo4j relationship type before inserting it into a Cypher string."""
    if not RELATIONSHIP_TYPE_PATTERN.match(relationship_type):
        raise ValueError(f"Invalid Neo4j relationship type: {relationship_type}")


def _validate_property_key(property_key: str) -> None:
    """Validate a Neo4j property key before inserting it into a Cypher string."""
    if not PROPERTY_KEY_PATTERN.match(property_key):
        raise ValueError(f"Invalid Neo4j property key: {property_key}")


def _labels_to_cypher(labels: list[str]) -> str:
    """Convert a list of labels into Cypher label syntax."""
    for label in labels:
        _validate_label(label)

    return "".join(f":{label}" for label in labels)


def create_or_update_node(tx: Any, node: GraphNode) -> None:
    """Create or update one node from graph-shaped JSON.

    Nodes are merged by their local stable id.
    """
    labels = _labels_to_cypher(node.labels)

    query = f"""
    MERGE (n{labels} {{id: $id}})
    SET n += $properties
    """

    tx.run(
        query,
        id=node.id,
        properties=node.properties,
    )


def _get_target_ref_match_clause(target_ref: TargetRef) -> tuple[str, dict[str, Any]]:
    """Create a safe MATCH clause for target_ref."""
    _validate_label(target_ref.label)
    _validate_property_key(target_ref.key)

    clause = f"(target:{target_ref.label} {{{target_ref.key}: $target_ref_value}})"
    parameters = {"target_ref_value": target_ref.value}

    return clause, parameters


def create_relationship_to_local_target(
    tx: Any,
    relationship: GraphRelationship,
) -> None:
    """Create a relationship where target is another local JSON node."""
    if relationship.target is None:
        raise ValueError("Local target relationship requires relationship.target.")

    _validate_relationship_type(relationship.type)

    query = f"""
    MATCH (source {{id: $source_id}})
    MATCH (target {{id: $target_id}})
    MERGE (source)-[r:{relationship.type}]->(target)
    SET r += $properties
    """

    result = tx.run(
        query,
        source_id=relationship.source,
        target_id=relationship.target,
        properties=relationship.properties,
    )

    summary = result.consume()
    if summary.counters.relationships_created == 0 and summary.counters.properties_set == 0:
        # This is not an error. The relationship may already exist.
        return


def create_relationship_to_target_ref(
    tx: Any,
    relationship: GraphRelationship,
) -> None:
    """Create a relationship where target is an existing vocabulary/control node."""
    if relationship.target_ref is None:
        raise ValueError("target_ref relationship requires relationship.target_ref.")

    _validate_relationship_type(relationship.type)

    target_match_clause, target_parameters = _get_target_ref_match_clause(
        relationship.target_ref
    )

    query = f"""
    MATCH (source {{id: $source_id}})
    MATCH {target_match_clause}
    MERGE (source)-[r:{relationship.type}]->(target)
    SET r += $properties
    RETURN count(target) AS target_count
    """

    parameters = {
        "source_id": relationship.source,
        "properties": relationship.properties,
        **target_parameters,
    }

    result = tx.run(query, **parameters)
    record = result.single()

    if record is None or record["target_count"] == 0:
        raise ValueError(
            "target_ref did not match an existing Neo4j node: "
            f"label={relationship.target_ref.label}, "
            f"key={relationship.target_ref.key}, "
            f"value={relationship.target_ref.value}"
        )


def load_graph_extraction_to_neo4j(
    extraction: GraphExtraction,
    clear_existing_instance_data: bool = False,
) -> dict[str, Any]:
    """Load a validated GraphExtraction object into Neo4j.

    Parameters
    ----------
    extraction:
        Validated graph-shaped JSON object.
    clear_existing_instance_data:
        If true, removes existing instance nodes before loading the sample graph.
        It does not remove control/vocabulary nodes such as ParameterType, Unit,
        EquipmentType, Concept, RelationshipDefinition, RequiredParameter.

    Returns
    -------
    dict[str, Any]
        Loading summary.
    """
    neo4j_config = get_neo4j_connection_config()

    driver = GraphDatabase.driver(
        neo4j_config["uri"],
        auth=(neo4j_config["user"], neo4j_config["password"]),
    )

    try:
        with driver.session(database=neo4j_config["database"]) as session:
            if clear_existing_instance_data:
                session.execute_write(clear_instance_graph)

            for node in extraction.nodes:
                session.execute_write(create_or_update_node, node)

            for relationship in extraction.relationships:
                if relationship.target is not None:
                    session.execute_write(
                        create_relationship_to_local_target,
                        relationship,
                    )
                elif relationship.target_ref is not None:
                    session.execute_write(
                        create_relationship_to_target_ref,
                        relationship,
                    )
                else:
                    raise ValueError(
                        "Relationship has neither target nor target_ref. "
                        "This should have been caught by validation."
                    )

    finally:
        driver.close()

    return {
        "document_id": extraction.document_id,
        "node_count": len(extraction.nodes),
        "relationship_count": len(extraction.relationships),
        "cleared_existing_instance_data": clear_existing_instance_data,
    }


def clear_instance_graph(tx: Any) -> None:
    """Remove instance graph nodes while keeping control/vocabulary graph nodes.

    This is useful for repeatedly loading the manual gold sample during development.
    """
    query = """
    MATCH (n)
    WHERE any(label IN labels(n) WHERE label IN [
        "Datasheet",
        "Equipment",
        "TechnicalParameter",
        "Evidence",
        "ExtractionRun",
        "ValidationIssue"
    ])
    DETACH DELETE n
    """

    tx.run(query)


def inspect_loaded_sample_graph() -> dict[str, Any]:
    """Return simple counts for loaded instance graph nodes and relationships."""
    neo4j_config = get_neo4j_connection_config()

    driver = GraphDatabase.driver(
        neo4j_config["uri"],
        auth=(neo4j_config["user"], neo4j_config["password"]),
    )

    try:
        with driver.session(database=neo4j_config["database"]) as session:
            node_rows = session.run(
                """
                MATCH (n)
                WHERE any(label IN labels(n) WHERE label IN [
                    "Datasheet",
                    "Equipment",
                    "TechnicalParameter",
                    "Evidence",
                    "ExtractionRun",
                    "ValidationIssue"
                ])
                RETURN labels(n) AS labels, count(n) AS count
                ORDER BY labels
                """
            )

            relationship_rows = session.run(
                """
                MATCH ()-[r]->()
                WHERE type(r) IN [
                    "DESCRIBES",
                    "HAS_EQUIPMENT_TYPE",
                    "HAS_PARAMETER",
                    "HAS_PARAMETER_TYPE",
                    "HAS_UNIT",
                    "EVIDENCED_BY",
                    "GENERATED_BY",
                    "ABOUT"
                ]
                RETURN type(r) AS relationship_type, count(r) AS count
                ORDER BY relationship_type
                """
            )

            return {
                "instance_node_counts": [dict(record) for record in node_rows],
                "relevant_relationship_counts": [
                    dict(record) for record in relationship_rows
                ],
            }

    finally:
        driver.close()