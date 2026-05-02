from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class GeneratedCqQuery(BaseModel):
    """Structured output returned by the LLM for one CQ validation check."""

    check_id: str = Field(
        description="The CQ validation check identifier from cq_validation_targets.yaml."
    )
    cypher_query: str = Field(
        description="A read-only Cypher query that answers the CQ validation check."
    )
    explanation: str = Field(
        description="Brief explanation of what the generated Cypher query checks."
    )


SYSTEM_MESSAGE = """You are a Neo4j Cypher expert.

Your task is to generate read-only Cypher queries for validating competency questions over a populated Neo4j instance graph.

Important safety rules:
- Generate only one Cypher query.
- The query must be read-only.
- The query must not modify the database.
- Do not use CREATE, MERGE, DELETE, DETACH DELETE, SET, REMOVE, DROP, CALL, LOAD CSV, FOREACH, CREATE CONSTRAINT, or CREATE INDEX.
- Do not include markdown fences.
- Do not include explanatory text inside the Cypher query.
- Return the query through the structured output field only.

General query rules:
- Return scalar properties only.
- Never return full Neo4j nodes, relationships, or paths.
- Do not return variables such as d, e, p, pt, u, ev directly.
- Always return explicit scalar properties such as d.id, e.id, p.id, pt.name, u.symbol, ev.source_text.
- Every expression in RETURN must use an explicit AS alias.
- The AS aliases must exactly match the required output column names.
- Every variable used in RETURN must be introduced earlier with MATCH or OPTIONAL MATCH.
- Do not invent property names.
- Use only the labels, relationships, and properties listed below.

Relevant labels:
- Datasheet
- Equipment
- EquipmentType
- TechnicalParameter
- ParameterType
- Unit
- Evidence
- ExtractionRun
- RequiredParameter

Relevant graph patterns:
- (Datasheet)-[:DESCRIBES]->(Equipment)
- (Equipment)-[:HAS_EQUIPMENT_TYPE]->(EquipmentType)
- (Equipment)-[:HAS_PARAMETER]->(TechnicalParameter)
- (TechnicalParameter)-[:HAS_PARAMETER_TYPE]->(ParameterType)
- (TechnicalParameter)-[:HAS_UNIT]->(Unit)
- (TechnicalParameter)-[:EVIDENCED_BY]->(Evidence)
- (TechnicalParameter)-[:GENERATED_BY]->(ExtractionRun)
- (RequiredParameter)-[:REQUIRES_PARAMETER_TYPE]->(ParameterType)
- (ParameterType)-[:ALLOWS_UNIT]->(Unit)

Important traversal guidance:
- To retrieve technical parameters with equipment context, start from:
  Equipment -[:HAS_PARAMETER]-> TechnicalParameter.
- To retrieve evidence with equipment context, use:
  Equipment -[:HAS_PARAMETER]-> TechnicalParameter -[:EVIDENCED_BY]-> Evidence.
- To retrieve normalized parameter type, use:
  TechnicalParameter -[:HAS_PARAMETER_TYPE]-> ParameterType.
- To retrieve unit information, use:
  TechnicalParameter -[:HAS_UNIT]-> Unit.
- To retrieve equipment type, use:
  Equipment -[:HAS_EQUIPMENT_TYPE]-> EquipmentType.
- Do not assume TechnicalParameter has equipment_id or product_model properties.
- Do not assume ParameterType has normalized, normalized_parameter_type, or category properties.

Available properties:

Datasheet:
- id
- file_name
- document_type

Equipment:
- id
- product_model
- manufacturer
- raw_equipment_type

EquipmentType:
- name
- display_name

TechnicalParameter:
- id
- raw_label
- value
- value_type

ParameterType:
- name
- display_name
- parameter_category
- expects_unit

Unit:
- symbol
- name

Evidence:
- id
- page_number
- content_block_id
- source_text
- evidence_type
- evidence_status
- confidence
- extraction_method

RequiredParameter:
- id
- reason

Column naming reminders:
- d.id AS datasheet_id
- d.file_name AS file_name
- d.document_type AS document_type
- e.id AS equipment_id
- e.product_model AS product_model
- e.manufacturer AS manufacturer
- e.raw_equipment_type AS raw_equipment_type
- et.name AS normalized_equipment_type
- et.display_name AS normalized_equipment_type_display_name
- p.id AS parameter_id
- p.raw_label AS raw_label
- p.value AS value
- p.value_type AS value_type
- pt.name AS normalized_parameter_type
- pt.name AS grounded_parameter_type
- pt.display_name AS parameter_display_name
- pt.parameter_category AS parameter_category
- pt.expects_unit AS parameter_type_expects_unit
- u.symbol AS unit
- u.symbol AS grounded_unit
- u.name AS unit_name
- ev.id AS evidence_id

CQ4 status rules:
- parameter_type_grounding_status must be "grounded" if pt IS NOT NULL, otherwise "not_grounded".
- unit_grounding_status must be:
  - "grounded" if u IS NOT NULL
  - "missing_unit_grounding" if u IS NULL and pt.expects_unit = true
  - "not_required" otherwise

The generated query must use the exact output column names required in the instruction.
"""

HUMAN_TEMPLATE = """Generate a read-only Cypher query for the following competency question validation target.

Check ID:
{check_id}

Description:
{description}

Expected result key:
{expected_result_key}

Instruction:
{instruction}

Output column requirements:
Follow the column names required in the instruction exactly.

Return a structured object with:
- check_id
- cypher_query
- explanation
"""


def create_chat_model() -> ChatOpenAI:
    """Create the LangChain chat model used for CQ Cypher generation.

    Environment variables:
    - OPENAI_API_KEY: required for OpenAI API access
    - LLM_MODEL: optional, defaults to gpt-4o-mini
    """
    load_dotenv()

    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")

    return ChatOpenAI(
        model=model_name,
        temperature=0,
    )


def generate_cq_query_for_target(
    target: dict[str, Any],
    llm: ChatOpenAI | None = None,
) -> GeneratedCqQuery:
    """Generate a read-only Cypher query for one CQ validation target."""
    if llm is None:
        llm = create_chat_model()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_MESSAGE),
            ("human", HUMAN_TEMPLATE),
        ]
    )

    structured_llm = llm.with_structured_output(GeneratedCqQuery)
    chain = prompt | structured_llm

    result = chain.invoke(
        {
            "check_id": target["check_id"],
            "description": target.get("description", ""),
            "expected_result_key": target.get("expected_result_key", ""),
            "instruction": target.get("instruction", ""),
        }
    )

    if not isinstance(result, GeneratedCqQuery):
        raise TypeError("LLM structured output did not return a GeneratedCqQuery instance.")

    return result


def generate_cq_queries_for_targets(
    targets: list[dict[str, Any]],
    llm: ChatOpenAI | None = None,
) -> list[GeneratedCqQuery]:
    """Generate read-only Cypher queries for multiple CQ validation targets."""
    if llm is None:
        llm = create_chat_model()

    generated_queries: list[GeneratedCqQuery] = []

    for target in targets:
        generated_query = generate_cq_query_for_target(target=target, llm=llm)
        generated_queries.append(generated_query)

    return generated_queries