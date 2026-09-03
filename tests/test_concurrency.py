from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator
from typing import Any

from conftest import wav_bytes
from fastapi.testclient import TestClient

from ai_tools_api.app import create_app
from ai_tools_api.config import Settings


class BlockingBackend:
    def __init__(self) -> None:
        self.stt_entered = threading.Event()
        self.tts_entered = threading.Event()
        self.llm_entered = threading.Event()
        self.release = threading.Event()

    async def transcribe(self, audio: bytes, language: str, timeout: float) -> str:
        del audio, language, timeout
        self.stt_entered.set()
        await asyncio.to_thread(self.release.wait)
        return "ok"

    async def synthesize(self, text: str, timeout: float) -> bytes:
        del text, timeout
        self.tts_entered.set()
        await asyncio.to_thread(self.release.wait)
        return wav_bytes()

    async def complete(self, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        del payload, timeout
        self.llm_entered.set()
        await asyncio.to_thread(self.release.wait)
        return {}

    async def stream(
        self, payload: dict[str, Any], timeout: float
    ) -> AsyncIterator[bytes]:
        del payload, timeout
        if False:
            yield b""


def request_tts(client: TestClient) -> object:
    return client.post(
        "/v1/audio/speech",
        json={
            "model": "piper-1",
            "voice": "en_US-lessac-medium",
            "input": "hold",
            "response_format": "wav",
        },
    )


def request_llm(client: TestClient) -> object:
    return client.post(
        "/v1/chat/completions",
        json={
            "model": "ggml-org/Qwen3.6-35B-A3B",
            "messages": [{"role": "user", "content": "hold"}],
        },
    )


def test_tts_overload_does_not_consume_stt_capacity() -> None:
    backend = BlockingBackend()
    client = TestClient(
        create_app(
            Settings(tts_concurrency=1, stt_concurrency=1),
            backend,
            backend,
            backend,
        )
    )
    thread = threading.Thread(target=request_tts, args=(client,))
    thread.start()
    assert backend.tts_entered.wait(1)
    overloaded = request_tts(client)
    assert overloaded.status_code == 429  # type: ignore[attr-defined]
    assert overloaded.json()["error"]["code"] == "overloaded"  # type: ignore[attr-defined]
    backend.release.set()
    thread.join(1)


def test_llm_has_an_independent_concurrency_limit() -> None:
    backend = BlockingBackend()
    client = TestClient(
        create_app(Settings(llm_concurrency=1), backend, backend, backend)
    )
    thread = threading.Thread(target=request_llm, args=(client,))
    thread.start()
    assert backend.llm_entered.wait(1)
    overloaded = request_llm(client)
    assert overloaded.status_code == 429  # type: ignore[attr-defined]
    assert overloaded.json()["error"]["code"] == "overloaded"  # type: ignore[attr-defined]
    backend.release.set()
    thread.join(1)
