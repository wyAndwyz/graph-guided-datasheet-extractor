from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class GeneratedCypherQuery(BaseModel):
    """Structured output returned by the LLM for one validation check."""

    check_id: str = Field(
        description="The validation check identifier from schema_validation_targets.yaml."
    )
    cypher_query: str = Field(
        description="A read-only Cypher query that answers the validation check."
    )
    explanation: str = Field(
        description="Brief explanation of what the generated Cypher query checks."
    )


SYSTEM_MESSAGE = """You are a Neo4j Cypher expert.

Your task is to generate read-only Cypher queries for validating a Neo4j control graph.

Important safety rules:
- Generate only one Cypher query.
- The query must be read-only.
- The query must not modify the database.
- Do not use CREATE, MERGE, DELETE, DETACH DELETE, SET, REMOVE, DROP, CALL, LOAD CSV, FOREACH, CREATE CONSTRAINT, or CREATE INDEX.
- Do not include markdown fences.
- Do not include explanatory text inside the Cypher query.
- Return the query through the structured output field only.

The Neo4j graph contains these relevant labels:
- Concept
- RelationshipDefinition
- ParameterType
- Unit
- EquipmentType
- RequiredParameter

The graph contains these relevant relationships:
- FROM_CONCEPT
- TO_CONCEPT
- INSTANCE_OF_CONCEPT
- REQUIRES_PARAMETER_TYPE
- ALLOWS_UNIT
"""


HUMAN_TEMPLATE = """Generate a read-only Cypher query for the following schema validation target.

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
    """Create the LangChain chat model used for Cypher generation.

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


def generate_cypher_for_target(
    target: dict[str, Any],
    llm: ChatOpenAI | None = None,
) -> GeneratedCypherQuery:
    """Generate a read-only Cypher query for one validation target using LangChain.

    Parameters
    ----------
    target:
        One validation target loaded from validation_specs/schema_validation_targets.yaml.
    llm:
        Optional pre-created ChatOpenAI instance. If not provided, a default model is created.

    Returns
    -------
    GeneratedCypherQuery
        Structured LLM output containing check_id, cypher_query, and explanation.
    """
    if llm is None:
        llm = create_chat_model()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_MESSAGE),
            ("human", HUMAN_TEMPLATE),
        ]
    )

    structured_llm = llm.with_structured_output(GeneratedCypherQuery)

    chain = prompt | structured_llm

    result = chain.invoke(
        {
            "check_id": target["check_id"],
            "description": target.get("description", ""),
            "expected_result_key": target.get("expected_result_key", ""),
            "instruction": target.get("instruction", ""),
        }
    )

    if not isinstance(result, GeneratedCypherQuery):
        raise TypeError(
            "LLM structured output did not return a GeneratedCypherQuery instance."
        )

    return result


def generate_cypher_for_targets(
    targets: list[dict[str, Any]],
    llm: ChatOpenAI | None = None,
) -> list[GeneratedCypherQuery]:
    """Generate read-only Cypher queries for multiple validation targets."""
    if llm is None:
        llm = create_chat_model()

    generated_queries: list[GeneratedCypherQuery] = []

    for target in targets:
        generated_query = generate_cypher_for_target(target=target, llm=llm)
        generated_queries.append(generated_query)

    return generated_queries