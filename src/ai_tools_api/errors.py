from __future__ import annotations

from typing import Any, Dict

from fastapi import Request
from fastapi.responses import JSONResponse

_MESSAGES = {
    "invalid_content_type": "The request content type is invalid.",
    "unsupported_model": "The requested model is not supported.",
    "unsupported_voice": "The requested voice is not supported.",
    "unsupported_format": "The response format is not supported.",
    "empty_input": "Speech input must not be empty.",
    "input_too_large": "Speech input is too large.",
    "audio_too_large": "The audio upload is too large.",
    "invalid_audio": "The audio upload is invalid.",
    "backend_unavailable": "The speech backend is unavailable.",
    "backend_failure": "The speech backend failed.",
    "timeout": "The speech request timed out.",
    "overloaded": "The speech service is busy.",
    "invalid_request": "The request is invalid.",
}


class ApiError(Exception):
    def __init__(self, code: str, status: int = 400) -> None:
        self.code = code
        self.status = status
        super().__init__(code)


def error_response(code: str, status: int) -> JSONResponse:
    body: Dict[str, Any] = {
        "error": {
            "message": _MESSAGES.get(code, _MESSAGES["invalid_request"]),
            "type": "invalid_request_error",
            "code": code,
        }
    }
    return JSONResponse(body, status_code=status)


async def api_error_handler(_request: Request, error: ApiError) -> JSONResponse:
    return error_response(error.code, error.status)
