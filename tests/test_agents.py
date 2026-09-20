"""Adapted original BaseAgent tests; no live model calls."""

import json
from mailo_cli.agents.base_agent import BaseAgent


class TestBaseAgent:
    """Test BaseAgent core functionality."""

    def test_init(self, tmp_path):
        agent = BaseAgent(
            api_key="test-key",
            model="mock-model",
            output_dir=tmp_path / "output",
        )
        assert agent.model == "mock-model"
        assert agent.max_tokens == 8192
        assert (tmp_path / "output").exists()

    def test_get_tools(self, tmp_path):
        agent = BaseAgent(api_key="test-key", model="mock-model", output_dir=tmp_path)
        tools = agent.get_tools()
        tool_names = [t["name"] for t in tools]
        assert "web_search" not in tool_names
        assert "web_fetch" not in tool_names
        assert "save_finding" in tool_names

    def test_save_finding(self, tmp_path):
        agent = BaseAgent(api_key="test-key", model="mock-model", output_dir=tmp_path)
        result = agent._save_finding(
            {
                "category": "case_law",
                "title": "Test Case C-634/21",
                "content": "Test content about SCHUFA.",
            }
        )
        assert "Finding saved" in result
        assert len(agent.collected_data) == 1
        assert agent.collected_data[0]["category"] == "case_law"
        assert "timestamp" in agent.collected_data[0]
        assert agent.collected_data[0]["agent"] == "research"

    def test_save_output(self, tmp_path):
        agent = BaseAgent(api_key="test-key", model="mock-model", output_dir=tmp_path)
        agent.save_output("test.md", "# Test Report\n\nContent here.")
        assert (tmp_path / "test.md").exists()
        assert "# Test Report" in (tmp_path / "test.md").read_text(encoding="utf-8")

    def test_save_collected_data(self, tmp_path):
        agent = BaseAgent(api_key="test-key", model="mock-model", output_dir=tmp_path)
        agent.collected_data = [
            {"category": "case_law", "title": "Test", "content": "Content"},
        ]
        agent.save_collected_data("test_findings.json")
        path = tmp_path / "test_findings.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data) == 1

    def test_cache_roundtrip(self, tmp_path):
        agent = BaseAgent(api_key="test-key", model="mock-model", output_dir=tmp_path)
        agent._write_cache("testkey", "cached content")
        result = agent._read_cache("testkey")
        assert result == "cached content"

    def test_cache_miss(self, tmp_path):
        agent = BaseAgent(api_key="test-key", model="mock-model", output_dir=tmp_path)
        result = agent._read_cache("nonexistent")
        assert result is None
