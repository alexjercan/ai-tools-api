from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

MODEL_ALIASES = (
    "ggml-org/Qwen3.6-35B-A3B",
    "ggml-org/gemma-4-26B-A4B-it-GGUF",
)
_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class FunctionCall(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    arguments: str

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        if not _NAME.fullmatch(value):
            raise PydanticCustomError("invalid_request", "Invalid function name")
        return value


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1, max_length=128)
    type: Literal["function"]
    function: FunctionCall


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = Field(default=None, min_length=1, max_length=128)
    tool_calls: list[ToolCall] | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def valid_role_fields(self) -> ChatMessage:
        if self.name is not None and not _NAME.fullmatch(self.name):
            raise PydanticCustomError("invalid_request", "Invalid message name")
        if self.role == "tool":
            if self.tool_call_id is None or self.content is None:
                raise PydanticCustomError("invalid_request", "Invalid tool message")
        elif self.tool_call_id is not None:
            raise PydanticCustomError("invalid_request", "Invalid tool call ID")
        if self.tool_calls is not None and self.role != "assistant":
            raise PydanticCustomError("invalid_request", "Invalid tool calls")
        if self.content is None and not self.tool_calls:
            raise PydanticCustomError("invalid_request", "Missing message content")
        return self


class FunctionDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    description: str | None = Field(default=None, max_length=4096)
    parameters: dict[str, Any]

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        if not _NAME.fullmatch(value):
            raise PydanticCustomError("invalid_request", "Invalid function name")
        return value


class FunctionTool(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal["function"]
    function: FunctionDefinition


class NamedToolChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        if not _NAME.fullmatch(value):
            raise PydanticCustomError("invalid_request", "Invalid function name")
        return value


class ToolChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal["function"]
    function: NamedToolChoice


class StreamOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    include_usage: bool = False


class ResponseFormat(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal["text", "json_object"]


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    model: str
    messages: list[ChatMessage] = Field(min_length=1, max_length=256)
    stream: bool = False
    stream_options: StreamOptions | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, gt=0, le=1)
    min_p: float | None = Field(default=None, ge=0, le=1)
    top_k: int | None = Field(default=None, ge=0, le=1000)
    max_tokens: int | None = Field(default=None, ge=1, le=32768)
    max_completion_tokens: int | None = Field(default=None, ge=1, le=32768)
    seed: int | None = None
    stop: str | list[str] | None = None
    frequency_penalty: float | None = Field(default=None, ge=-2, le=2)
    presence_penalty: float | None = Field(default=None, ge=-2, le=2)
    tools: list[FunctionTool] | None = Field(default=None, max_length=32)
    tool_choice: Literal["none", "auto", "required"] | ToolChoice | None = None
    response_format: ResponseFormat | None = None
    n: Literal[1] = 1

    @field_validator("model")
    @classmethod
    def supported_model(cls, value: str) -> str:
        if value not in MODEL_ALIASES:
            raise PydanticCustomError("unsupported_model", "Unsupported model")
        return value

    @field_validator("stop")
    @classmethod
    def bounded_stop(cls, value: str | list[str] | None) -> str | list[str] | None:
        values = [value] if isinstance(value, str) else value or []
        if len(values) > 4 or any(
            not item or len(item.encode("utf-8")) > 256 for item in values
        ):
            raise PydanticCustomError("invalid_request", "Invalid stop sequence")
        return value

    @model_validator(mode="after")
    def valid_combination(self, info: ValidationInfo) -> ChatCompletionRequest:
        if self.stream_options is not None and not self.stream:
            raise PydanticCustomError(
                "invalid_request", "Stream options require streaming"
            )
        if self.max_tokens is not None and self.max_completion_tokens is not None:
            raise PydanticCustomError("invalid_request", "Duplicate token limit")
        if self.tool_choice not in (None, "none") and not self.tools:
            raise PydanticCustomError("invalid_request", "Tool choice requires tools")
        tool_names = {tool.function.name for tool in self.tools or []}
        if (
            isinstance(self.tool_choice, ToolChoice)
            and self.tool_choice.function.name not in tool_names
        ):
            raise PydanticCustomError("invalid_request", "Unknown tool choice")
        limit = (info.context or {}).get("max_request_bytes", 1024 * 1024)
        try:
            encoded = json.dumps(
                self.model_dump(mode="json"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise PydanticCustomError(
                "invalid_request", "Invalid JSON value"
            ) from error
        if len(encoded) > limit:
            raise PydanticCustomError("input_too_large", "Chat input too large")
        return self

    def backend_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)
