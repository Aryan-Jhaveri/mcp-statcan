"""Shared pytest fixtures."""

import pytest

from src.api.sdmx import sdmx_tools


@pytest.fixture(autouse=True)
def clear_structure_cache():
    """The DSD cache is module-level; isolate tests that mock different structures."""
    sdmx_tools._structure_cache.clear()
    yield
    sdmx_tools._structure_cache.clear()
