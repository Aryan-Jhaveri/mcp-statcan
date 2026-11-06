"""fetch_structure_xml: truncated DSDs are retried and never cached; stalls fail fast (#145)."""

import asyncio

import httpx
import pytest
import respx
from httpx import Response

from src import config
from src.api.sdmx import sdmx_tools
from src.api.sdmx.sdmx_tools import fetch_structure_xml

from tests.sdmx_fixtures import DSD_XML, STRUCTURE_URL

TRUNCATED = DSD_XML[: len(DSD_XML) // 2]


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def _instant(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", _instant)


@respx.mock
@pytest.mark.asyncio
async def test_good_body_is_cached():
    route = respx.get(STRUCTURE_URL).mock(return_value=Response(200, text=DSD_XML))
    assert await fetch_structure_xml(18100004) == DSD_XML
    assert await fetch_structure_xml(18100004) == DSD_XML
    assert route.call_count == 1
    assert 18100004 in sdmx_tools._structure_cache


@respx.mock
@pytest.mark.asyncio
async def test_truncated_body_is_retried_and_not_cached():
    route = respx.get(STRUCTURE_URL).mock(
        side_effect=[Response(200, text=TRUNCATED), Response(200, text=DSD_XML)]
    )
    assert await fetch_structure_xml(18100004) == DSD_XML
    assert route.call_count == 2
    assert sdmx_tools._structure_cache[18100004][1] == DSD_XML


@respx.mock
@pytest.mark.asyncio
async def test_truncated_every_time_raises_clear_error_and_caches_nothing():
    route = respx.get(STRUCTURE_URL).mock(return_value=Response(200, text=TRUNCATED))
    # The WDS fallback (#175) fails too, so the original error still surfaces
    respx.post(f"{config.BASE_URL}/getCubeMetadata").mock(return_value=Response(500))
    with pytest.raises(httpx.ReadError, match="incomplete structure.*WDS metadata failed"):
        await fetch_structure_xml(18100004)
    assert route.call_count == config.SDMX_STRUCTURE_ATTEMPTS
    assert 18100004 not in sdmx_tools._structure_cache
    assert 18100004 not in sdmx_tools._fallback_structure_cache


@respx.mock
@pytest.mark.asyncio
async def test_stall_is_retried():
    route = respx.get(STRUCTURE_URL).mock(
        side_effect=[httpx.ReadTimeout("stalled"), Response(200, text=DSD_XML)]
    )
    assert await fetch_structure_xml(18100004) == DSD_XML
    assert route.call_count == 2


def test_structure_timeout_fails_fast():
    # A stall used to wait 20 s per attempt; the acceptance bar is ~10 s added
    assert config.SDMX_STRUCTURE_TIMEOUT <= 10
