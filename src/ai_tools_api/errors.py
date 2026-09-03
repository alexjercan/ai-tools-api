from __future__ import annotations

from typing import Any, Dict, Union

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(alias="message")
    type: str = Field(alias="type")
    code: str = Field(alias="code")


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    error: ErrorDetail = Field(alias="error")


ERROR_RESPONSES: Dict[Union[int, str], Dict[str, Any]] = {
    status: {"model": ErrorEnvelope} for status in (400, 413, 415, 429, 502, 503, 504)
}


_MESSAGES = {
    "invalid_content_type": "The request content type is invalid.",
    "unsupported_model": "The requested model is not supported.",
    "unsupported_voice": "The requested voice is not supported.",
    "unsupported_format": "The response format is not supported.",
    "empty_input": "Speech input must not be empty.",
    "input_too_large": "The request input is too large.",
    "audio_too_large": "The audio upload is too large.",
    "invalid_audio": "The audio upload is invalid.",
    "backend_unavailable": "The inference backend is unavailable.",
    "backend_failure": "The inference backend failed.",
    "timeout": "The inference request timed out.",
    "overloaded": "The inference service is busy.",
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
