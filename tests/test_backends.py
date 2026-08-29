from __future__ import annotations

import asyncio

import pytest
from conftest import wav_bytes

from ai_tools_api.backends import PiperService
from ai_tools_api.errors import ApiError
from ai_tools_api.wav import valid_wav


def test_wav_validation() -> None:
    valid = wav_bytes()
    assert valid_wav(valid)
    assert not valid_wav(b"")
    assert not valid_wav(valid[:-1])
    assert not valid_wav(b"NOPE" + valid[4:])


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
