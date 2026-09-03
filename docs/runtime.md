# Runtime, configuration, and deployment

`nix run .` uses a Nix-generated launcher to start the owned `whisper-server` on
`127.0.0.1:10301` and the owned `llama-server` model router on
`127.0.0.1:10302`, waits up to 30 seconds for both sockets, then starts the API
on `127.0.0.1:10300`. The launcher records and signals only its child PIDs.
Piper runs per request without a shell. Uploads remain in bounded memory;
framework-level multipart spooling uses private temporary storage under the
systemd deployment.

Initial limits are 25 MiB per audio file, 4,096 UTF-8 bytes per synthesis input,
64 MiB backend output, 16 KiB incomplete HTTP/1 events, 64 total ASGI
connections, two concurrent STT requests, two concurrent TTS requests, one LLM
request, 120 seconds per STT request, 60 seconds per TTS request, 600 seconds per
LLM request, and 512 bytes per client error. Chat requests are limited to 1 MiB
and complete JSON or SSE backend output is limited to 16 MiB. Uvicorn keeps idle
connections for 5 seconds. Multipart framing permits 64 KiB above the file
limit. Pydantic settings read `.env`; all environment names start with
`AI_TOOLS_API_` and match the names in `src/ai_tools_api/config.py`. Bounds in
that model reject unsafe values.

The Home Manager module is disabled by default under `services.ai-tools-api`.
It installs separate Whisper, llama.cpp, and API systemd user services. The API
requires both loopback backend units and waits for their sockets. All units use
private temporary storage, strict system protection, no new privileges, bounded
restart, and bounded stop. The model router has two hash-pinned Q8 GGUF models:
Qwen3.6 35B A3B and Gemma 4 26B A4B. The module package can be overridden for a
CUDA host.
A private deployment may set `host` to its Tailscale address. Do not expose the
service publicly. The Whisper endpoint always binds loopback. There is no token,
account, proxy, router, Funnel, telemetry, or external call except fixed-output
model fetches.

## Local protocol check

Start with `nix run .`. In another terminal, synthesize and inspect a fixture:

```sh
curl --fail http://127.0.0.1:10300/v1/audio/speech \
  -H 'content-type: application/json' \
  -d '{"model":"piper-1","voice":"en_US-lessac-medium","input":"The build passed.","response_format":"wav"}' \
  -o fixture.wav
file fixture.wav
curl --fail http://127.0.0.1:10300/v1/audio/transcriptions \
  -F file=@fixture.wav -F model=whisper-1 | jq
curl --fail http://127.0.0.1:10300/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"model":"ggml-org/Qwen3.6-35B-A3B","messages":[{"role":"user","content":"Reply with OK."}]}' | jq
```

Press Ctrl-C in the foreground service terminal to stop both processes. Unit
tests inject mocks for both service interfaces. This repository does not retest
Whisper or Piper inference behavior.
