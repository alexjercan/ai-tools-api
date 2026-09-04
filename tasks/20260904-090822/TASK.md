# Fix implicit llama backend read timeout

- STATUS: CLOSED
- PRIORITY: 100
- TAGS: api

## Goal

Make the configured LLM timeout control the complete backend operation. Do not
let the HTTP client's implicit five-second read timeout reject valid slow
inference as an unavailable backend.

## Diagnosis

The deployed API used an outer 600-second `asyncio.timeout`, but each temporary
`httpx.AsyncClient` retained HTTPX's default five-second per-operation timeout.
Gemma completed short bounded generations, while an ordinary `hello` took about
11 seconds without response bytes. HTTPX raised `ReadTimeout`; the adapter then
mapped it to `backend_unavailable`. Direct curl requests to llama.cpp succeeded.

## Decisions

- Replace HTTPX's implicit timeout with the configured timeout for both paths.
- Keep the existing outer timeout as the whole-operation bound.
- Map an HTTPX timeout to the stable `timeout` error, not `backend_unavailable`.
- Add regression tests for both client configuration and sanitized errors.

## Verification

- `nix develop -c bash -lc 'ruff format --check . && ruff check . && mypy src && pytest'` passed. All 24 tests passed; the one warning is the known upstream Starlette HTTPX deprecation.
- `nix flake check -L` passed all eight checks on x86_64-linux.
- `nix build .#ai-tools-api -L` passed.
- The fixed adapter completed the production Gemma `hello` request through the
  llama.cpp router with 79 completion tokens, exceeding the former five-second
  read timeout without error.

