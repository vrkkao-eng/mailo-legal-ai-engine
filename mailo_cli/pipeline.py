"""Finding validation and export boundary for the extracted research pipeline."""

import json
from pathlib import Path
from urllib.parse import urlsplit
from rdflib import Graph
from mailo_cli.exporters.graph_exporter import KnowledgeGraphExporter

CATEGORIES = {
    "case_law",
    "legal_principle",
    "literature",
    "patent",
    "compliance_risk",
    "obligation",
    "technology",
}


def validate_findings(findings):
    if not isinstance(findings, list) or not findings:
        raise ValueError("Expected a nonempty JSON array of findings")
    for i, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise ValueError(f"Finding {i} must be an object")
        for field in ("category", "title", "content", "source_url"):
            if not isinstance(finding.get(field), str) or not finding[field].strip():
                raise ValueError(f"Finding {i} requires nonempty {field}")
        if finding["category"] not in CATEGORIES:
            raise ValueError(f"Unknown finding category: {finding['category']}")
        source = urlsplit(finding["source_url"])
        if (
            source.scheme not in ("http", "https")
            or not source.hostname
            or source.username
        ):
            raise ValueError("source_url must be an HTTP(S) URL without credentials")
        if not isinstance(finding.get("metadata", {}), dict):
            raise ValueError("metadata must be an object")
    return findings


def export_findings(findings, output_dir: Path):
    validate_findings(findings)
    exporter = KnowledgeGraphExporter(output_dir)
    exporter._export_jsonld(findings)
    path = output_dir / "medical_ai_knowledge_graph.jsonld"
    graph = Graph().parse(data=path.read_text(encoding="utf-8"), format="json-ld")
    graph.serialize(destination=str(output_dir / "findings.ttl"), format="turtle")
    return {"findings": len(findings), "triples": len(graph)}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
