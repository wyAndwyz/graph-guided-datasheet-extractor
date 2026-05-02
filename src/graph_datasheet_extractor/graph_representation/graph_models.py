from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class TargetRef(BaseModel):
    """Reference to an existing Neo4j vocabulary/control node.

    TargetRef is used when a relationship points to a node that is not created
    by the current graph-shaped JSON document, but already exists in the Neo4j
    control/vocabulary graph.

    Example:
        {
            "label": "ParameterType",
            "key": "name",
            "value": "Dimensions"
        }
    """

    label: str = Field(
        min_length=1,
        description="Neo4j label of the referenced vocabulary/control node.",
    )
    key: str = Field(
        min_length=1,
        description="Property key used to identify the referenced node.",
    )
    value: str | int | float | bool = Field(
        description="Property value used to identify the referenced node.",
    )


class GraphNode(BaseModel):
    """Node object in the graph-shaped JSON format."""

    id: str = Field(
        min_length=1,
        description="Stable local node identifier used inside this JSON document.",
    )
    labels: list[str] = Field(
        min_length=1,
        description="Neo4j labels assigned to this node.",
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Neo4j node properties.",
    )

    @model_validator(mode="after")
    def validate_labels(self) -> "GraphNode":
        """Ensure labels are non-empty strings."""
        if any(not isinstance(label, str) or not label.strip() for label in self.labels):
            raise ValueError(f"Node '{self.id}' contains an empty or invalid label.")

        return self


class GraphRelationship(BaseModel):
    """Relationship object in the graph-shaped JSON format.

    A relationship must use exactly one target form:

    1. target:
       The target node is another node inside the same JSON document.

    2. target_ref:
       The target node already exists in the Neo4j control/vocabulary graph.
    """

    source: str = Field(
        min_length=1,
        description="ID of the source node in the local graph-shaped JSON document.",
    )
    type: str = Field(
        min_length=1,
        description="Neo4j relationship type.",
    )
    target: str | None = Field(
        default=None,
        description="ID of the target node in the same graph-shaped JSON document.",
    )
    target_ref: TargetRef | None = Field(
        default=None,
        description="Reference to an existing Neo4j vocabulary/control node.",
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional relationship properties.",
    )

    @model_validator(mode="after")
    def validate_target_choice(self) -> "GraphRelationship":
        """Ensure exactly one of target or target_ref is provided."""
        has_target = self.target is not None
        has_target_ref = self.target_ref is not None

        if has_target == has_target_ref:
            raise ValueError(
                "Each relationship must define exactly one of 'target' or 'target_ref'."
            )

        return self


class GraphExtraction(BaseModel):
    """Top-level graph-shaped JSON extraction document."""

    schema_version: str = Field(
        min_length=1,
        description="Version of the graph-shaped JSON format.",
    )
    document_id: str = Field(
        min_length=1,
        description="Stable identifier of the source datasheet/document.",
    )
    source_file: str | None = Field(
        default=None,
        description="Local path to the source file.",
    )
    extraction_scope: Literal[
        "manual_gold_sample",
        "llm_generated",
        "llm_repaired",
        "human_reviewed",
    ] = Field(
        description="How this graph-shaped extraction was produced.",
    )
    description: str | None = Field(
        default=None,
        description="Optional human-readable description.",
    )
    nodes: list[GraphNode] = Field(
        min_length=1,
        description="Nodes created by this extraction result.",
    )
    relationships: list[GraphRelationship] = Field(
        default_factory=list,
        description="Relationships created by this extraction result.",
    )

    @model_validator(mode="after")
    def validate_node_ids_are_unique(self) -> "GraphExtraction":
        """Ensure all node IDs are unique."""
        node_ids = [node.id for node in self.nodes]

        if len(node_ids) != len(set(node_ids)):
            duplicates = sorted(
                node_id for node_id in set(node_ids) if node_ids.count(node_id) > 1
            )
            raise ValueError(f"Duplicate node IDs found: {duplicates}")

        return self

    @model_validator(mode="after")
    def validate_relationship_local_references(self) -> "GraphExtraction":
        """Ensure local relationship references point to existing local nodes."""
        node_ids = {node.id for node in self.nodes}

        for relationship in self.relationships:
            if relationship.source not in node_ids:
                raise ValueError(
                    f"Relationship source '{relationship.source}' does not exist in nodes."
                )

            if relationship.target is not None and relationship.target not in node_ids:
                raise ValueError(
                    f"Relationship target '{relationship.target}' does not exist in nodes."
                )

        return self

    @model_validator(mode="after")
    def validate_document_id_has_datasheet_node(self) -> "GraphExtraction":
        """Ensure document_id corresponds to a Datasheet node ID."""
        matching_nodes = [
            node
            for node in self.nodes
            if node.id == self.document_id and "Datasheet" in node.labels
        ]

        if not matching_nodes:
            raise ValueError(
                "document_id must match the id of a node with label 'Datasheet'."
            )

        return self

    def get_node_by_id(self, node_id: str) -> GraphNode | None:
        """Return a node by local ID, or None if not found."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_nodes_by_label(self, label: str) -> list[GraphNode]:
        """Return all nodes containing a given label."""
        return [node for node in self.nodes if label in node.labels]

    def get_relationships_by_type(self, relationship_type: str) -> list[GraphRelationship]:
        """Return all relationships with a given relationship type."""
        return [
            relationship
            for relationship in self.relationships
            if relationship.type == relationship_type
        ]