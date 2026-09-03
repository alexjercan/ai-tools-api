from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    host: str = Field(
        default="127.0.0.1",
        alias="AI_TOOLS_API_HOST",
        description="Public API bind address.",
    )
    port: int = Field(
        default=10300,
        ge=1,
        le=65535,
        alias="AI_TOOLS_API_PORT",
        description="Public API TCP port.",
    )
    whisper_url: HttpUrl = Field(
        default=HttpUrl("http://127.0.0.1:10301/private-inference"),
        alias="AI_TOOLS_API_WHISPER_URL",
        description="Private loopback Whisper inference URL.",
    )

    llama_url: HttpUrl = Field(
        default=HttpUrl("http://127.0.0.1:10302/v1/chat/completions"),
        alias="AI_TOOLS_API_LLAMA_URL",
        description="Private loopback llama.cpp chat completions URL.",
    )

    @field_validator("whisper_url", "llama_url")
    @classmethod
    def loopback_backend_url(cls, value: HttpUrl) -> HttpUrl:
        if (
            value.scheme != "http"
            or value.host not in {"127.0.0.1", "localhost", "::1"}
            or value.username is not None
            or value.password is not None
            or value.query is not None
            or value.fragment is not None
        ):
            raise ValueError("Backend URL must use plain HTTP on loopback")
        return value

    piper_executable: str = Field(
        default="piper",
        alias="AI_TOOLS_API_PIPER",
        description="Absolute path to the owned Piper executable.",
    )
    piper_model: str = Field(
        default="",
        alias="AI_TOOLS_API_PIPER_MODEL",
        description="Absolute path to the owned Piper voice model.",
    )
    piper_config: str = Field(
        default="",
        alias="AI_TOOLS_API_PIPER_CONFIG",
        description="Absolute path to the owned Piper voice configuration.",
    )
    max_upload_bytes: int = Field(
        default=25 * 1024 * 1024,
        ge=1,
        le=64 * 1024 * 1024,
        alias="AI_TOOLS_API_MAX_UPLOAD_BYTES",
        description="Maximum accepted transcription audio bytes.",
    )
    max_text_bytes: int = Field(
        default=4096,
        ge=1,
        le=65536,
        alias="AI_TOOLS_API_MAX_TEXT_BYTES",
        description="Maximum accepted synthesis input UTF-8 bytes.",
    )
    max_backend_output_bytes: int = Field(
        default=64 * 1024 * 1024,
        ge=1024,
        le=128 * 1024 * 1024,
        alias="AI_TOOLS_API_MAX_OUTPUT_BYTES",
        description="Maximum captured speech backend response bytes.",
    )
    llm_max_request_bytes: int = Field(
        default=1024 * 1024,
        ge=1024,
        le=8 * 1024 * 1024,
        alias="AI_TOOLS_API_LLM_MAX_REQUEST_BYTES",
        description="Maximum chat completion request bytes.",
    )
    llm_max_output_bytes: int = Field(
        default=16 * 1024 * 1024,
        ge=1024,
        le=128 * 1024 * 1024,
        alias="AI_TOOLS_API_LLM_MAX_OUTPUT_BYTES",
        description="Maximum chat completion backend response bytes.",
    )
    stt_concurrency: int = Field(
        default=2,
        ge=1,
        le=32,
        alias="AI_TOOLS_API_STT_CONCURRENCY",
        description="Maximum concurrent transcription requests.",
    )
    tts_concurrency: int = Field(
        default=2,
        ge=1,
        le=32,
        alias="AI_TOOLS_API_TTS_CONCURRENCY",
        description="Maximum concurrent synthesis requests.",
    )
    llm_concurrency: int = Field(
        default=1,
        ge=1,
        le=32,
        alias="AI_TOOLS_API_LLM_CONCURRENCY",
        description="Maximum concurrent chat completion requests.",
    )
    stt_timeout_seconds: float = Field(
        default=120.0,
        ge=0.1,
        le=600,
        alias="AI_TOOLS_API_STT_TIMEOUT",
        description="Transcription backend timeout in seconds.",
    )
    tts_timeout_seconds: float = Field(
        default=60.0,
        ge=0.1,
        le=600,
        alias="AI_TOOLS_API_TTS_TIMEOUT",
        description="Synthesis backend timeout in seconds.",
    )
    llm_timeout_seconds: float = Field(
        default=600.0,
        ge=0.1,
        le=3600,
        alias="AI_TOOLS_API_LLM_TIMEOUT",
        description="Chat completion backend timeout in seconds.",
    )
    startup_timeout_seconds: float = Field(
        default=30.0,
        ge=0.1,
        le=600,
        alias="AI_TOOLS_API_STARTUP_TIMEOUT",
        description="Backend readiness timeout in seconds.",
    )
    shutdown_grace_seconds: float = Field(
        default=3.0,
        ge=0.1,
        le=600,
        alias="AI_TOOLS_API_SHUTDOWN_GRACE",
        description="Owned child process termination grace in seconds.",
    )
