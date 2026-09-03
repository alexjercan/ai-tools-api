import signal

import uvicorn

from ai_tools_api.app import create_app
from ai_tools_api.backends import (
    trusted_llama_service,
    trusted_piper_service,
    trusted_whisper_service,
)
from ai_tools_api.config import Settings


def main() -> None:
    settings = Settings()
    transcription_service = trusted_whisper_service(settings)
    synthesis_service = trusted_piper_service(settings)
    generation_service = trusted_llama_service(settings)
    app = create_app(
        settings, transcription_service, synthesis_service, generation_service
    )
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
        access_log=False,
        timeout_keep_alive=5,
        limit_concurrency=64,
        h11_max_incomplete_event_size=16 * 1024,
    )
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    uvicorn.Server(config).run()


if __name__ == "__main__":
    main()
