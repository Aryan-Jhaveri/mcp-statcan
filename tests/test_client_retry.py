"""Shared HTTP helpers: stalls are retried, and fail fast on no first byte (#161)."""

import asyncio

import httpx
import pytest
import respx
from httpx import Response

from src import config
from src.api import client
from src.api.client import make_get_request, make_post_request, make_sdmx_get

POST_URL = f"{config.BASE_URL}/getSeriesInfoFromVector"
GET_URL = f"{config.BASE_URL}/getCodeSets"
SDMX_URL = f"{config.SDMX_BASE_URL}data/DF_18100004/2.2"
BODY = [{"vectorId": 2063945}]
OK = [{"status": "SUCCESS", "object": {"vectorId": 2063945}}]


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def _instant(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", _instant)


@respx.mock
@pytest.mark.asyncio
@pytest.mark.parametrize("stall", [httpx.ReadTimeout("stalled"), httpx.ConnectTimeout("no connect")])
async def test_post_stall_is_retried(stall):
    route = respx.post(POST_URL).mock(side_effect=[stall, Response(200, json=OK)])
    assert await make_post_request("/getSeriesInfoFromVector", BODY) == OK
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_post_dropped_connection_is_retried():
    route = respx.post(POST_URL).mock(
        side_effect=[httpx.RemoteProtocolError("closed"), Response(200, json=OK)]
    )
    assert await make_post_request("/getSeriesInfoFromVector", BODY) == OK
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_post_stalls_exhausted_reraise():
    route = respx.post(POST_URL).mock(side_effect=httpx.ReadTimeout("stalled"))
    with pytest.raises(httpx.ReadTimeout):
        await make_post_request("/getSeriesInfoFromVector", BODY)
    assert route.call_count == client._MAX_RETRY_ATTEMPTS


@respx.mock
@pytest.mark.asyncio
async def test_post_4xx_is_not_retried():
    route = respx.post(POST_URL).mock(return_value=Response(400, json={"message": "bad"}))
    with pytest.raises(httpx.HTTPStatusError):
        await make_post_request("/getSeriesInfoFromVector", BODY)
    assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_post_5xx_is_still_retried():
    route = respx.post(POST_URL).mock(side_effect=[Response(503), Response(200, json=OK)])
    assert await make_post_request("/getSeriesInfoFromVector", BODY) == OK
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_get_and_sdmx_stalls_are_retried():
    get_route = respx.get(GET_URL).mock(side_effect=[httpx.ReadTimeout("stalled"), Response(200, json={})])
    sdmx_route = respx.get(SDMX_URL).mock(side_effect=[httpx.ReadTimeout("stalled"), Response(200, text="<x/>")])
    assert await make_get_request("/getCodeSets") == {}
    assert (await make_sdmx_get(SDMX_URL)).text == "<x/>"
    assert get_route.call_count == 2 and sdmx_route.call_count == 2


def test_timeouts_fail_fast_on_no_first_byte():
    t = client._timeout(config.TIMEOUT_LARGE, None)
    # A stall used to wait the whole 30-120 s; the bar is ~10 s per stall
    assert t.read == config.HTTP_FIRST_BYTE_TIMEOUT <= 10
    assert t.connect == config.HTTP_CONNECT_TIMEOUT <= 10
    # The caller's budget still bounds every phase, and an endpoint can ask for longer
    assert client._timeout(5.0, None).read == 5.0
    assert client._timeout(config.TIMEOUT_LARGE, 60.0).read == 60.0
