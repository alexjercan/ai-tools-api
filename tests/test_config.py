from __future__ import annotations

import pytest

from ai_tools_api.config import Settings


def test_configuration_defaults_and_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 10300
    assert settings.stt_concurrency == 2
    assert settings.tts_concurrency == 2
    assert settings.llm_concurrency == 1
    assert str(settings.llama_url) == "http://127.0.0.1:10302/v1/chat/completions"
    monkeypatch.setenv("AI_TOOLS_API_STT_CONCURRENCY", "0")
    with pytest.raises(ValueError):
        Settings()


def test_backend_urls_are_loopback_http() -> None:
    for url in (
        "https://127.0.0.1/chat",
        "http://example.com/chat",
        "http://user@127.0.0.1/chat",
        "http://127.0.0.1/chat?token=secret",
    ):
        with pytest.raises(ValueError):
            Settings(llama_url=url)
