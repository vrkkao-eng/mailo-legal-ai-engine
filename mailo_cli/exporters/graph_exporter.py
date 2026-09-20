"""JSON-LD exporter extracted and hardened from DH_THESIS; see ATTRIBUTION.md."""

import json
import hashlib
from pathlib import Path
from rich.console import Console

console = Console(stderr=True)


class KnowledgeGraphExporter:
    JSONLD_CONTEXT = {
        "mailo": "https://w3id.org/mailo#",
        "@vocab": "https://w3id.org/mailo#",
        "dcterms": "http://purl.org/dc/terms/",
        "eli": "http://data.europa.eu/eli/ontology#",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "label": "http://www.w3.org/2000/01/rdf-schema#label",
        "description": "dcterms:description",
        "source": {"@id": "dcterms:source", "@type": "@id"},
        "date": {"@id": "dcterms:date", "@type": "xsd:date"},
        "cites": {"@id": "cites", "@type": "@id"},
        "hasPrinciple": {"@id": "hasPrinciple", "@type": "@id"},
        "interpretsArticle": {"@id": "interpretsArticle", "@type": "@id"},
        "governedBy": {"@id": "governedBy", "@type": "@id"},
        "hasRisk": {"@id": "hasRisk", "@type": "@id"},
        "conflictsWith": {"@id": "conflictsWith", "@type": "@id"},
        "complementedBy": {"@id": "complementedBy", "@type": "@id"},
    }

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _export_jsonld(self, findings: list[dict]):
        """Generate JSON-LD knowledge graph."""
        graph_nodes = []
        for f in findings:
            node = {
                "@id": "urn:mailo:finding:"
                + hashlib.sha256(
                    json.dumps(f, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest(),
                "@type": self._map_category_to_type(f.get("category", "unknown")),
                "label": f.get("title", ""),
                "description": f.get("content", ""),
            }
            if f.get("source_url"):
                node["source"] = f["source_url"]
            meta = f.get("metadata", {})
            if meta.get("date") or meta.get("year"):
                node["date"] = {
                    "@value": str(meta.get("date") or meta["year"]),
                    "@type": "xsd:date" if meta.get("date") else "xsd:gYear",
                }
            graph_nodes.append(node)

        doc = {
            "@context": self.JSONLD_CONTEXT,
            "@graph": graph_nodes,
        }

        out_path = self.output_dir / "medical_ai_knowledge_graph.jsonld"
        out_path.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        console.print(f"  [green]JSON-LD:[/] {out_path} ({len(graph_nodes)} nodes)")

    @staticmethod
    def _safe_id(text: str) -> str:
        import re

        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", text[:60])
        safe = re.sub(r"_+", "_", safe).strip("_")
        return safe or "unknown"

    @staticmethod
    def _map_category_to_type(category: str) -> str:
        type_map = {
            "case_law": "CJEUCase",
            "legal_principle": "LegalPrinciple",
            "literature": "LiteratureSource",
            "patent": "UPCCase",
            "compliance_risk": "ComplianceRisk",
            "obligation": "ComplianceObligation",
            "technology": "Technology",
        }
        return type_map.get(category, "Thing")
