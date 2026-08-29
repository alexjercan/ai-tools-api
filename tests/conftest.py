from __future__ import annotations

import struct
from typing import List, Tuple

import pytest
from fastapi.testclient import TestClient

from ai_tools_api.app import create_app
from ai_tools_api.config import Settings


def wav_bytes() -> bytes:
    data = b"\x00\x00" * 8
    fmt = struct.pack("<HHIIHH", 1, 1, 16000, 32000, 2, 16)
    body = b"fmt " + struct.pack("<I", 16) + fmt
    body += b"data" + struct.pack("<I", len(data)) + data
    return b"RIFF" + struct.pack("<I", len(body) + 4) + b"WAVE" + body


class RecordingBackend:
    def __init__(self) -> None:
        self.stt_calls: List[Tuple[bytes, str, float]] = []
        self.tts_calls: List[Tuple[str, float]] = []

    async def transcribe(self, audio: bytes, language: str, timeout: float) -> str:
        self.stt_calls.append((audio, language, timeout))
        return "The transcribed message."

    async def synthesize(self, text: str, timeout: float) -> bytes:
        self.tts_calls.append((text, timeout))
        return wav_bytes()


@pytest.fixture
def backend() -> RecordingBackend:
    return RecordingBackend()


@pytest.fixture
def client(backend: RecordingBackend) -> TestClient:
    return TestClient(
        create_app(Settings(max_upload_bytes=1024, max_text_bytes=64), backend, backend)
    )
