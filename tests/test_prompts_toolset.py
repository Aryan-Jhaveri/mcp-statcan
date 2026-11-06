"""MCP prompts may only name tools that the active toolset registers."""

import re

import pytest

from src.prompts import _PROMPTS, get_prompt_text
from src.server import create_server, registry

TOOL_NAME = re.compile(r"\b(get_[a-z_]+|search_cubes_by_title|query_[a-z_]+|fetch_[a-z_]+)\b")
ARGS = {"topic": "labour force", "analysis_goal": "trend", "product_id": "14100287", "vector_ids": "v1 v2"}


def _registered(toolset: str, http_mode: bool) -> set:
    registry._tools.clear()
    registry._handlers.clear()
    create_server(http_mode=http_mode, toolset=toolset)
    names = {t.name for t in registry.get_tools()}
    registry._tools.clear()
    registry._handlers.clear()
    return names


def _mentioned(texts) -> set:
    return {m for t in texts for m in TOOL_NAME.findall(t)}


@pytest.mark.parametrize("toolset", ["legacy", "core"])
@pytest.mark.parametrize("http_mode", [True, False])
def test_prompts_name_only_registered_tools(toolset, http_mode):
    registered = _registered(toolset, http_mode)
    texts = [get_prompt_text(n, ARGS, toolset) for n in _PROMPTS]
    texts += [p.description or "" for p in _PROMPTS.values()]
    missing = _mentioned(texts) - registered
    assert not missing, f"{toolset} (http={http_mode}) prompts name unregistered tools: {missing}"


def test_core_prompts_use_core_wording():
    text = "\n".join(get_prompt_text(n, ARGS, "core") for n in _PROMPTS)
    assert "query_sdmx" not in text and "get_sdmx_key_for_dimension" not in text
    assert "search=" in text and "sql=" in text and "vectorId" in text


def test_toolset_defaults_from_env(monkeypatch):
    monkeypatch.setenv("STATCAN_TOOLSET", "core")
    assert "query_sdmx" not in get_prompt_text("statcan-download", ARGS)
    monkeypatch.setenv("STATCAN_TOOLSET", "legacy")
    assert "query_sdmx" in get_prompt_text("statcan-download", ARGS)
