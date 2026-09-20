"""Adapted original JSON-LD exporter tests."""

import json
from mailo_cli.exporters.graph_exporter import KnowledgeGraphExporter


class TestKnowledgeGraphExporter:
    """Test KnowledgeGraphExporter class."""

    def test_init(self, tmp_path):
        exporter = KnowledgeGraphExporter(output_dir=tmp_path / "kg")
        assert (tmp_path / "kg").exists()

    def test_safe_id(self):
        assert KnowledgeGraphExporter._safe_id("Hello World!") == "Hello_World"
        assert KnowledgeGraphExporter._safe_id("C-634/21") == "C-634_21"

    def test_map_category(self):
        assert KnowledgeGraphExporter._map_category_to_type("case_law") == "CJEUCase"
        assert KnowledgeGraphExporter._map_category_to_type("unknown") == "Thing"

    def test_export_jsonld(self, tmp_path):
        exporter = KnowledgeGraphExporter(output_dir=tmp_path)
        findings = [
            {
                "category": "case_law",
                "title": "Test Case",
                "content": "Content",
                "metadata": {},
            }
        ]
        exporter._export_jsonld(findings)
        out = tmp_path / "medical_ai_knowledge_graph.jsonld"
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "@context" in data
        assert "@graph" in data
        assert len(data["@graph"]) == 1
