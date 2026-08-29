from __future__ import annotations

import pytest

from ai_tools_api.config import Settings


def test_configuration_defaults_and_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 10300
    assert settings.stt_concurrency == 2
    assert settings.tts_concurrency == 2
    monkeypatch.setenv("AI_TOOLS_API_STT_CONCURRENCY", "0")
    with pytest.raises(ValueError):
        Settings()
