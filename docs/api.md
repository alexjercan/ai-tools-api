# Public API contract

Release 0.1 has two public routes. All other paths return 404. OpenAPI, Swagger,
and Redoc routes are disabled.

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

## Errors

Errors use `{"error":{"message":"...","type":"invalid_request_error","code":"..."}}`.
Stable codes are `invalid_content_type`, `unsupported_model`,
`unsupported_voice`, `unsupported_format`, `empty_input`, `input_too_large`,
`audio_too_large`, `invalid_audio`, `backend_unavailable`, `backend_failure`,
`timeout`, `overloaded`, and `invalid_request`. Error bodies stay below 512
bytes and omit backend details.
