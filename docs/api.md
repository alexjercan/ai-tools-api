# Public API contract

The API has three inference routes. Swagger is available at `/docs` and its
schema at `/openapi.json`. Redoc is disabled. All other paths return 404.

## Transcription

`POST /v1/audio/transcriptions` requires `multipart/form-data` fields `file` and
`model=whisper-1`. Optional fields are `language` (default `auto`) and
`response_format=json`. Recognized bounded audio containers are WAV, MP3, Ogg,
FLAC, WebM, and MP4. Success is `{"text":"..."}`.

## Synthesis

`POST /v1/audio/speech` requires JSON fields `model=piper-1`,
`voice=en_US-lessac-medium`, `input`, and `response_format=wav`. Unknown fields
are rejected. Input must be non-empty strict UTF-8 without C0 or DEL control
characters. Success is validated RIFF/WAVE bytes with `Content-Type: audio/wav`.
The service never plays audio.

## Chat completions

`POST /v1/chat/completions` accepts a strict OpenAI-compatible JSON subset. The
required fields are `model` and a non-empty `messages` array. Supported models
are `ggml-org/Qwen3.6-35B-A3B` and
`ggml-org/gemma-4-26B-A4B-it-GGUF`. Messages support `system`, `user`,
`assistant`, and `tool` roles with text content. Assistant tool calls and tool
results are supported.

Optional generation fields are `stream`, `stream_options.include_usage`,
`temperature`, `top_p`, `min_p`, `top_k`, `max_tokens`,
`max_completion_tokens`, `seed`, `stop`, `frequency_penalty`,
`presence_penalty`, `tools`, `tool_choice`, `response_format`, and `n=1`.
`response_format.type` is `text` or `json_object`. At most 256 messages, 32
tools, four stop sequences, and one completion are accepted. Unknown fields are
rejected.

A non-streaming success is a validated OpenAI chat completion JSON object.
`stream=true` returns validated server-sent events with
`Content-Type: text/event-stream` and ends with `data: [DONE]`. The stream holds
one LLM concurrency slot until completion or client cancellation.

## Errors

Errors use `{"error":{"message":"...","type":"invalid_request_error","code":"..."}}`.
Stable codes are `invalid_content_type`, `unsupported_model`,
`unsupported_voice`, `unsupported_format`, `empty_input`, `input_too_large`,
`audio_too_large`, `invalid_audio`, `backend_unavailable`, `backend_failure`,
`timeout`, `overloaded`, and `invalid_request`. Error bodies stay below 512
bytes and omit backend details.
