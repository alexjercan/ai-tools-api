from __future__ import annotations

from conftest import RecordingBackend, wav_bytes
from fastapi.testclient import TestClient


def error_code(response: object) -> str:
    return response.json()["error"]["code"]  # type: ignore[attr-defined,no-any-return]


def test_only_contract_routes_are_exposed(client: TestClient) -> None:
    for path in ("/redoc", "/", "/inference", "/v1/models"):
        assert client.get(path).status_code == 404
    assert client.get("/v1/audio/speech").status_code == 405
    assert client.get("/v1/audio/transcriptions").status_code == 405


def test_transcription_normalizes_response(
    client: TestClient, backend: RecordingBackend
) -> None:
    response = client.post(
        "/v1/audio/transcriptions",
        files={"file": ("fixture.wav", wav_bytes(), "audio/wav")},
        data={"model": "whisper-1"},
    )
    assert response.status_code == 200
    assert response.json() == {"text": "The transcribed message."}
    assert backend.stt_calls[0][1] == "auto"


def test_transcription_validation(client: TestClient) -> None:
    route = "/v1/audio/transcriptions"
    assert error_code(client.post(route, content=b"x")) == "invalid_content_type"
    assert (
        error_code(client.post(route, files={"file": ("x", wav_bytes())}))
        == "invalid_request"
    )
    unsupported = client.post(
        route,
        files={"file": ("x", wav_bytes())},
        data={"model": "other"},
    )
    assert error_code(unsupported) == "unsupported_model"
    unsupported_format = client.post(
        route,
        files={"file": ("x", wav_bytes())},
        data={"model": "whisper-1", "response_format": "text"},
    )
    assert error_code(unsupported_format) == "unsupported_format"
    empty = client.post(route, files={"file": ("x", b"")}, data={"model": "whisper-1"})
    assert error_code(empty) == "invalid_audio"
    malformed = client.post(
        route, files={"file": ("x", b"not audio")}, data={"model": "whisper-1"}
    )
    assert error_code(malformed) == "invalid_audio"
    large = client.post(
        route,
        files={"file": ("x", b"RIFF" + b"x" * 1100)},
        data={"model": "whisper-1"},
    )
    assert error_code(large) == "audio_too_large"


def test_speech_returns_validated_wav(
    client: TestClient, backend: RecordingBackend
) -> None:
    response = client.post(
        "/v1/audio/speech",
        json={
            "model": "piper-1",
            "voice": "en_US-lessac-medium",
            "input": "The build passed.",
            "response_format": "wav",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content[:4] == b"RIFF"
    assert backend.tts_calls[0][0] == "The build passed."


def test_speech_field_and_text_policy(client: TestClient) -> None:
    base = {
        "model": "piper-1",
        "voice": "en_US-lessac-medium",
        "input": "ok",
        "response_format": "wav",
    }
    assert (
        error_code(client.post("/v1/audio/speech", content=b"{}"))
        == "invalid_content_type"
    )
    for field, value, code in (
        ("model", "x", "unsupported_model"),
        ("voice", "x", "unsupported_voice"),
        ("response_format", "mp3", "unsupported_format"),
    ):
        request = base | {field: value}
        assert error_code(client.post("/v1/audio/speech", json=request)) == code
    for text, code in (
        ("", "empty_input"),
        ("   ", "empty_input"),
        ("bad\ntext", "invalid_request"),
    ):
        assert (
            error_code(client.post("/v1/audio/speech", json=base | {"input": text}))
            == code
        )
    assert (
        error_code(client.post("/v1/audio/speech", json=base | {"input": "x" * 65}))
        == "input_too_large"
    )
    assert (
        error_code(client.post("/v1/audio/speech", json=base | {"extra": 1}))
        == "invalid_request"
    )


def test_errors_are_small_and_do_not_leak(client: TestClient) -> None:
    response = client.post("/v1/audio/speech", json={})
    assert len(response.content) < 512
    assert response.json() == {
        "error": {
            "message": "The request is invalid.",
            "type": "invalid_request_error",
            "code": "invalid_request",
        }
    }
    assert b"traceback" not in response.content.lower()
    assert b"/nix/store" not in response.content
