# Add bounded llama.cpp chat completions

- STATUS: CLOSED
- PRIORITY: 100
- TAGS: api, nix, llm

## Goal

Make `ai-tools-api` the sole owner and bounded public gateway for the existing
llama.cpp deployment. Preserve the Qwen and Gemma model aliases.

## Contract decisions

- Add the exact public route `POST /v1/chat/completions`.
- Support non-streaming JSON and streaming SSE responses.
- Expose a strict OpenAI-compatible request subset. Reject unknown fields.
- Include bounded tool calling and `stream_options` support.
- Keep the llama.cpp backend on loopback. Do not expose backend details.
- Preserve model aliases `ggml-org/Qwen3.6-35B-A3B` and
  `ggml-org/gemma-4-26B-A4B-it-GGUF`.
- Use immutable hash-pinned model inputs rather than mutable runtime downloads.
  Preserve the exact Q8 files. They use about 59.37 GiB in total. This replaces
  equivalent mutable cache storage after migration; temporary duplication is
  acceptable while the old cache still exists.

## Implementation

- Add typed chat validation, a generation service protocol, and a bounded
  llama.cpp HTTP adapter.
- Add independent request, response, concurrency, and timeout settings.
- Propagate streaming cancellation and bound each stream and total duration.
- Add focused API, adapter, overload, timeout, malformed output, and leakage
  tests with fake backends.
- Add an owned `ai-tools-api-llama` service and launcher child supervision.
- Add Home Manager options for the package, model preset, port, and limits.
- Update API and deployment documentation.
- After release, migrate `nix.dotfiles` away from its system llama.cpp service.

## Verification

Recorded on 2026-09-03:

- `ruff format --check .`: passed, 29 files formatted.
- `ruff check .`: passed.
- `mypy src`: passed, 9 source files.
- `pytest`: passed, 22 tests. One upstream Starlette `httpx` deprecation
  warning remains.
- `alejandra --check flake.nix nix`: passed.
- `nix flake check -L`: passed on x86_64-linux. The incompatible
  aarch64-linux output was evaluated but not built.
- `nix build .#ai-tools-api -L`: passed. Both fixed-output Q8 model hashes were
  verified. The complete closure is 61.7 GiB.
- `nix build .#checks.x86_64-linux.module-evaluation -L`: passed.
- A temporary fake model preset started the installed llama.cpp router on a
  loopback test port. The process was stopped by its recorded PID.
- Real model inference remains opt-in and was not run.

