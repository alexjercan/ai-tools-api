from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest
from conftest import wav_bytes

from ai_tools_api.backends import LlamaService, PiperService
from ai_tools_api.errors import ApiError
from ai_tools_api.wav import valid_wav


def test_wav_validation() -> None:
    valid = wav_bytes()
    assert valid_wav(valid)
    assert not valid_wav(b"")
    assert not valid_wav(valid[:-1])
    assert not valid_wav(b"NOPE" + valid[4:])


def completion_response() -> dict[str, object]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "test",
        "choices": [],
    }


def test_llama_completion_and_stream_validation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.content.find(b'"stream":true') >= 0:
            content = (
                b'data: {"id":"x","object":"chat.completion.chunk",'
                b'"model":"test","choices":[]}\n\n'
                b"data: [DONE]\n\n"
            )
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=content
            )
        return httpx.Response(200, json=completion_response())

    service = LlamaService("http://127.0.0.1/chat", 4096, httpx.MockTransport(handler))
    result = asyncio.run(service.complete({"stream": False}, 1))
    assert result["object"] == "chat.completion"

    async def collect() -> bytes:
        return b"".join([event async for event in service.stream({"stream": True}, 1)])

    assert asyncio.run(collect()).endswith(b"data: [DONE]\n\n")


def test_llama_uses_only_configured_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    original_client = httpx.AsyncClient
    client_timeouts: list[object] = []

    def client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        client_timeouts.append(kwargs.get("timeout", "missing"))
        return original_client(*args, **kwargs)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.content.find(b'"stream":true') >= 0:
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=b"data: [DONE]\n\n",
            )
        return httpx.Response(200, json=completion_response())

    monkeypatch.setattr(httpx, "AsyncClient", client)
    service = LlamaService("http://127.0.0.1/chat", 4096, httpx.MockTransport(handler))
    asyncio.run(service.complete({"stream": False}, 1))

    async def collect() -> None:
        async for _event in service.stream({"stream": True}, 1):
            pass

    asyncio.run(collect())
    assert client_timeouts == [1, 1]


def test_llama_http_timeout_is_sanitized() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("/secret/backend stalled")

    service = LlamaService("http://127.0.0.1/chat", 4096, httpx.MockTransport(handler))
    with pytest.raises(ApiError) as raised:
        asyncio.run(service.complete({}, 1))
    assert raised.value.code == "timeout"
    assert "/secret" not in str(raised.value)


def test_llama_malformed_output_is_sanitized() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": "application/json"}, content=b"/secret"
        )

    service = LlamaService("http://127.0.0.1/chat", 4096, httpx.MockTransport(handler))
    with pytest.raises(ApiError) as raised:
        asyncio.run(service.complete({}, 1))
    assert raised.value.code == "backend_failure"
    assert "/secret" not in str(raised.value)


def test_llama_stream_rejects_missing_done() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=(
                b'data: {"id":"x","object":"chat.completion.chunk",'
                b'"model":"test","choices":[]}\n\n'
            ),
        )

    service = LlamaService("http://127.0.0.1/chat", 4096, httpx.MockTransport(handler))

    async def consume() -> None:
        async for _event in service.stream({}, 1):
            pass

    with pytest.raises(ApiError) as raised:
        asyncio.run(consume())
    assert raised.value.code == "backend_failure"


def test_llama_stream_closes_on_cancellation() -> None:
    class BlockingStream(httpx.AsyncByteStream):
        def __init__(self) -> None:
            self.entered = asyncio.Event()
            self.closed = False

        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield (
                b'data: {"id":"x","object":"chat.completion.chunk",'
                b'"model":"test","choices":[]}\n\n'
            )
            self.entered.set()
            await asyncio.Event().wait()

        async def aclose(self) -> None:
            self.closed = True

    stream = BlockingStream()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, stream=stream
        )

    service = LlamaService("http://127.0.0.1/chat", 4096, httpx.MockTransport(handler))

    async def cancel() -> None:
        async def consume() -> None:
            async for _event in service.stream({}, 10):
                pass

        task = asyncio.create_task(consume())
        await asyncio.wait_for(stream.entered.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel())
    assert stream.closed


def test_llama_timeout_is_sanitized() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.05)
        return httpx.Response(200, json=completion_response())

    service = LlamaService("http://127.0.0.1/chat", 4096, httpx.MockTransport(handler))
    with pytest.raises(ApiError) as raised:
        asyncio.run(service.complete({}, 0.01))
    assert raised.value.code == "timeout"


def test_llama_output_limit() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"x" * 2048,
        )

    service = LlamaService("http://127.0.0.1/chat", 1024, httpx.MockTransport(handler))
    with pytest.raises(ApiError) as raised:
        asyncio.run(service.complete({}, 1))
    assert raised.value.code == "backend_failure"


def test_backend_unavailable_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    async def unavailable(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise OSError("/secret/piper failed")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", unavailable)
    service = PiperService("/piper", "/model", "", 1024)
    with pytest.raises(ApiError) as raised:
        asyncio.run(service.synthesize("hello", 1))
    assert raised.value.code == "backend_unavailable"
    assert "/secret" not in str(raised.value)
