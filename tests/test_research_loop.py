from types import SimpleNamespace as NS
from unittest.mock import MagicMock
import pytest
from mailo_cli.agents.base_agent import BaseAgent


def agent(tmp_path):
    a = BaseAgent("test-key", tmp_path, model="mock-model")
    a.allowed_sources = {"https://example.org/source"}
    return a


@pytest.mark.asyncio
async def test_tool_roundtrip_and_provenance(tmp_path):
    a = agent(tmp_path)
    a.client.messages.create = MagicMock(
        side_effect=[
            NS(
                content=[
                    NS(
                        type="tool_use",
                        name="save_finding",
                        id="call1",
                        input={
                            "category": "case_law",
                            "title": "Synthetic",
                            "content": "Text",
                            "source_url": "https://example.org/source",
                        },
                    )
                ],
                stop_reason="tool_use",
            ),
            NS(content=[NS(type="text", text="Complete")], stop_reason="end_turn"),
        ]
    )
    assert await a.run_agent("Synthetic input") == "Complete"
    assert len(a.collected_data) == 1
    assert a.collected_data[0]["agent"] == "research"
    assert a.client.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_unknown_source_rejected(tmp_path):
    a = agent(tmp_path)
    with pytest.raises(ValueError, match="source was not supplied"):
        await a.execute_tool(
            "save_finding",
            {
                "category": "case_law",
                "title": "x",
                "content": "x",
                "source_url": "https://example.org/invented",
            },
        )


@pytest.mark.asyncio
async def test_max_turns_fails(tmp_path):
    a = agent(tmp_path)
    a.MAX_TURNS = 1
    a.client.messages.create = MagicMock(
        return_value=NS(
            content=[
                NS(
                    type="tool_use",
                    name="save_finding",
                    id="call1",
                    input={
                        "category": "case_law",
                        "title": "x",
                        "content": "x",
                        "source_url": "https://example.org/source",
                    },
                )
            ],
            stop_reason="tool_use",
        )
    )
    with pytest.raises(RuntimeError, match="max turns"):
        await a.run_agent("input")


@pytest.mark.asyncio
async def test_token_limit_is_not_success(tmp_path):
    a = agent(tmp_path)
    a.client.messages.create = MagicMock(
        return_value=NS(
            content=[NS(type="text", text="Partial")], stop_reason="max_tokens"
        )
    )
    with pytest.raises(RuntimeError, match="Incomplete"):
        await a.run_agent("input")
