from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Dict, NamedTuple, Tuple

from fastapi import Body, Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
)
from pydantic_core import PydanticCustomError
from starlette.middleware.base import RequestResponseEndpoint

from ai_tools_api.backends import (
    GenerationService,
    SynthesisService,
    TranscriptionService,
)
from ai_tools_api.chat import ChatCompletionRequest
from ai_tools_api.config import Settings
from ai_tools_api.errors import (
    ERROR_RESPONSES,
    ApiError,
    api_error_handler,
    error_response,
)
from ai_tools_api.gates import ConcurrencyGate

logger = logging.getLogger("ai_tools_api")
_LANGUAGE = re.compile(r"^(auto|[A-Za-z]{2,3}(?:-[A-Za-z]{2,4})?)$")


class TranscriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)

    model: str = Field(alias="model")
    language: str = Field(default="auto", alias="language")
    response_format: str = Field(default="json", alias="response_format")

    @field_validator("model")
    @classmethod
    def supported_model(cls, value: str) -> str:
        if value != "whisper-1":
            raise PydanticCustomError("unsupported_model", "Unsupported model")
        return value

    @field_validator("language")
    @classmethod
    def supported_language(cls, value: str) -> str:
        if not _LANGUAGE.fullmatch(value):
            raise PydanticCustomError("invalid_request", "Invalid language")
        return value

    @field_validator("response_format")
    @classmethod
    def supported_format(cls, value: str) -> str:
        if value != "json":
            raise PydanticCustomError("unsupported_format", "Unsupported format")
        return value


class SpeechRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)

    model: str = Field(alias="model")
    voice: str = Field(alias="voice")
    input: str = Field(
        alias="input",
        min_length=1,
        pattern=r"^[^\x00-\x1f\x7f]+$",
    )
    response_format: str = Field(alias="response_format")

    @field_validator("model")
    @classmethod
    def supported_model(cls, value: str) -> str:
        if value != "piper-1":
            raise PydanticCustomError("unsupported_model", "Unsupported model")
        return value

    @field_validator("voice")
    @classmethod
    def supported_voice(cls, value: str) -> str:
        if value != "en_US-lessac-medium":
            raise PydanticCustomError("unsupported_voice", "Unsupported voice")
        return value

    @field_validator("response_format")
    @classmethod
    def supported_format(cls, value: str) -> str:
        if value != "wav":
            raise PydanticCustomError("unsupported_format", "Unsupported format")
        return value

    @field_validator("input", mode="before")
    @classmethod
    def non_blank_input(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise PydanticCustomError("empty_input", "Empty input")
        return value

    @field_validator("input")
    @classmethod
    def bounded_input(cls, value: str, info: ValidationInfo) -> str:
        try:
            encoded = value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as error:
            raise PydanticCustomError("invalid_request", "Invalid input") from error
        limit = (info.context or {}).get("max_text_bytes", 65536)
        if len(encoded) > limit:
            raise PydanticCustomError("input_too_large", "Input too large")
        return value


class AudioResponse(Response):
    media_type = "audio/wav"


class RequestPolicy(NamedTuple):
    content_type: str
    content_type_prefix: bool
    max_request_bytes: int
    oversized_code: str
    require_declared_size: bool = False


def _declared_size(request: Request) -> int | None:
    value = request.headers.get("content-length")
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return -1


def _content_type_matches(request: Request, policy: RequestPolicy) -> bool:
    content_type = request.headers.get("content-type", "").lower()
    if policy.content_type_prefix:
        return content_type.startswith(policy.content_type)
    return content_type.split(";", 1)[0].strip() == policy.content_type


def _looks_like_audio(header: bytes) -> bool:
    return (
        (len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE")
        or header.startswith((b"ID3", b"OggS", b"fLaC", b"\x1aE\xdf\xa3"))
        or (len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0)
        or (len(header) >= 12 and header[4:8] == b"ftyp")
    )


async def _read_audio(upload: UploadFile, limit: int) -> bytes:
    content = bytearray()
    try:
        while chunk := await upload.read(64 * 1024):
            content.extend(chunk)
            if len(content) > limit:
                raise ApiError("audio_too_large", 413)
    finally:
        await upload.close()
    audio = bytes(content)
    if not audio or not _looks_like_audio(audio[:16]):
        raise ApiError("invalid_audio")
    return audio


def create_app(
    settings: Settings,
    transcription_service: TranscriptionService,
    synthesis_service: SynthesisService,
    generation_service: GenerationService,
) -> FastAPI:
    app = FastAPI(
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
    policies: Dict[Tuple[str, str], RequestPolicy] = {
        ("POST", "/v1/audio/transcriptions"): RequestPolicy(
            "multipart/form-data;",
            True,
            settings.max_upload_bytes + 65536,
            "audio_too_large",
        ),
        ("POST", "/v1/audio/speech"): RequestPolicy(
            "application/json",
            False,
            settings.max_text_bytes + 4096,
            "input_too_large",
        ),
        ("POST", "/v1/chat/completions"): RequestPolicy(
            "application/json",
            False,
            settings.llm_max_request_bytes,
            "input_too_large",
            True,
        ),
    }

    @app.middleware("http")
    async def enforce_request_policy(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        started = time.monotonic()
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))[:64]
        response: Response
        policy = policies.get((request.method, request.url.path))
        if policy is not None and not _content_type_matches(request, policy):
            response = error_response("invalid_content_type", 415)
        elif policy is not None and (
            ((size := _declared_size(request)) is None and policy.require_declared_size)
            or (size is not None and (size < 0 or size > policy.max_request_bytes))
        ):
            response = error_response(policy.oversized_code, 413)
        else:
            response = await call_next(request)
        logger.info(
            "request_id=%s endpoint=%s duration_ms=%d result=%d",
            request_id,
            request.url.path,
            int((time.monotonic() - started) * 1000),
            response.status_code,
        )
        return response

    stt_gate = ConcurrencyGate(settings.stt_concurrency)
    tts_gate = ConcurrencyGate(settings.tts_concurrency)
    llm_gate = ConcurrencyGate(settings.llm_concurrency)

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        code = error.errors()[0].get("type", "invalid_request")
        supported = {
            "unsupported_model",
            "unsupported_voice",
            "unsupported_format",
            "empty_input",
            "input_too_large",
            "invalid_request",
        }
        if code not in supported:
            code = "invalid_request"
        return error_response(code, 413 if code == "input_too_large" else 400)

    def parse_transcription(
        model: Annotated[str, Form()],
        language: Annotated[str, Form()] = "auto",
        response_format: Annotated[str, Form()] = "json",
    ) -> TranscriptionRequest:
        try:
            return TranscriptionRequest.model_validate(
                {
                    "model": model,
                    "language": language,
                    "response_format": response_format,
                }
            )
        except ValidationError as error:
            raise RequestValidationError(error.errors()) from error

    def parse_speech(
        payload: Annotated[SpeechRequest, Body()],
    ) -> SpeechRequest:
        try:
            return SpeechRequest.model_validate(
                payload.model_dump(by_alias=True),
                context={"max_text_bytes": settings.max_text_bytes},
            )
        except ValidationError as error:
            raise RequestValidationError(error.errors()) from error

    def parse_chat(
        payload: Annotated[ChatCompletionRequest, Body()],
    ) -> ChatCompletionRequest:
        try:
            return ChatCompletionRequest.model_validate(
                payload.model_dump(mode="json"),
                context={"max_request_bytes": settings.llm_max_request_bytes},
            )
        except ValidationError as error:
            raise RequestValidationError(error.errors()) from error

    @app.post("/v1/audio/transcriptions", responses=ERROR_RESPONSES)
    async def transcriptions(
        file: Annotated[UploadFile, File()],
        request: TranscriptionRequest = Depends(parse_transcription),  # noqa: B008
    ) -> Dict[str, str]:
        audio = await _read_audio(file, settings.max_upload_bytes)
        async with stt_gate:
            text = await transcription_service.transcribe(
                audio, request.language, settings.stt_timeout_seconds
            )
        return {"text": text}

    @app.post("/v1/chat/completions", responses=ERROR_RESPONSES)
    async def chat_completions(
        request: ChatCompletionRequest = Depends(parse_chat),  # noqa: B008
    ) -> Response:
        payload = request.backend_payload()
        if not request.stream:
            async with llm_gate:
                completion = await generation_service.complete(
                    payload, settings.llm_timeout_seconds
                )
            return JSONResponse(completion)

        async def events() -> AsyncIterator[bytes]:
            async with llm_gate:
                async for event in generation_service.stream(
                    payload, settings.llm_timeout_seconds
                ):
                    yield event

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post(
        "/v1/audio/speech",
        response_class=AudioResponse,
        responses=ERROR_RESPONSES,
    )
    async def speech(
        request: SpeechRequest = Depends(parse_speech),  # noqa: B008
    ) -> Response:
        async with tts_gate:
            wav = await synthesis_service.synthesize(
                request.input, settings.tts_timeout_seconds
            )
        return AudioResponse(wav)

    return app
