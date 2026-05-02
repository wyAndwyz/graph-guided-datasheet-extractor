from __future__ import annotations

import re


FORBIDDEN_KEYWORDS = [
    "CREATE",
    "MERGE",
    "DELETE",
    "DETACH DELETE",
    "SET",
    "REMOVE",
    "DROP",
    "CALL",
    "LOAD CSV",
    "FOREACH",
    "CREATE CONSTRAINT",
    "CREATE INDEX",
    "DROP CONSTRAINT",
    "DROP INDEX",
]

ALLOWED_START_KEYWORDS = [
    "MATCH",
    "OPTIONAL MATCH",
    "WITH",
]


def strip_cypher_comments(query: str) -> str:
    """Remove single-line Cypher comments starting with //."""
    lines = []
    for line in query.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("//"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def assert_read_only_cypher(query: str) -> None:
    """Raise ValueError if a Cypher query contains unsafe write operations.

    This checker is intentionally conservative. It is designed for LLM-generated
    validation queries, which should only inspect the graph and never modify it.
    """
    cleaned_query = strip_cypher_comments(query)

    if not cleaned_query:
        raise ValueError("Cypher query is empty.")

    normalized = re.sub(r"\s+", " ", cleaned_query).strip().upper()

    # Remove one trailing semicolon if present.
    if normalized.endswith(";"):
        normalized = normalized[:-1].strip()

    if not any(normalized.startswith(keyword) for keyword in ALLOWED_START_KEYWORDS):
        raise ValueError(
            "Only read-only Cypher queries starting with MATCH, OPTIONAL MATCH, or WITH are allowed."
        )

    for keyword in FORBIDDEN_KEYWORDS:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, normalized):
            raise ValueError(f"Unsafe Cypher keyword detected: {keyword}")

    # Prevent multiple statements in one query.
    if ";" in normalized:
        raise ValueError("Multiple Cypher statements are not allowed.")


def is_read_only_cypher(query: str) -> bool:
    """Return True if the query passes the read-only safety check."""
    try:
        assert_read_only_cypher(query)
        return True
    except ValueError:
        return False