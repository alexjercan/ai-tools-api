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

    @field_validator("whisper_url")
    @classmethod
    def loopback_whisper_url(cls, value: HttpUrl) -> HttpUrl:
        if value.host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Whisper URL must use loopback")
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
        description="Maximum captured backend response bytes.",
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
    startup_timeout_seconds: float = Field(
        default=30.0,
        ge=0.1,
        le=600,
        alias="AI_TOOLS_API_STARTUP_TIMEOUT",
        description="Whisper readiness timeout in seconds.",
    )
    shutdown_grace_seconds: float = Field(
        default=3.0,
        ge=0.1,
        le=600,
        alias="AI_TOOLS_API_SHUTDOWN_GRACE",
        description="Owned child process termination grace in seconds.",
    )
