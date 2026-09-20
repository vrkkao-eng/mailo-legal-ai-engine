"""Shared application services used by the CLI and HTTP adapters."""

from pathlib import Path

from rdflib import Graph


def execute_packaged_query(ontology_turtle: str, query_path: Path):
    """Run a reviewed packaged SELECT query against Turtle supplied by a caller."""
    graph = Graph().parse(data=ontology_turtle, format="turtle")
    result = graph.query(query_path.read_text(encoding="utf-8"))
    return [
        {
            str(variable): str(row[variable]) if row[variable] is not None else None
            for variable in result.vars
        }
        for row in result
    ]
