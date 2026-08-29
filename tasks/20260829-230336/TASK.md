# Implement bounded speech API runtime

- STATUS: CLOSED
- PRIORITY: 100
- TAGS: api

## Scope

Create the standalone `ai-tools-api` repository. Release 0.1 exposes only
transcription and synthesis while the product remains suitable for later
tracked tools.

## Decisions

- Use FastAPI, Pydantic models and validators, Pydantic Settings with `.env`,
  and uv2nix from a locked `uv.lock`.
- Keep transcription and synthesis as separate injected service interfaces.
- Keep mocks only under `tests`; do not ship fake runtime backends.
- Buffer uploads in bounded memory. Do not create repository-managed upload
  files.
- Let Nix compose `whisper-server` and the API for `nix run`. Home Manager uses
  separate Whisper and API systemd user services.
- Keep the Piper stdout-close patch. The pinned nixpkgs Piper 1.7.0 source still
  lacks the close before reading the temporary WAV. A focused package build
  proved the corrected patch applies and Python byte-compilation succeeds.
- Package each Piper model beside its `.onnx.json` configuration. Piper 1.7.0
  accepts but ignores `--config` and infers the adjacent file path.
- Do not retest Whisper or Piper inference. Test only API behavior, adapters,
  process invocation, Nix composition, and module evaluation.
- Do not inspect source text or dependency closures as tests.
- Keep durable documentation to the public API contract and complex runtime and
  deployment behavior.

## Verification

- `nix develop -c bash -lc 'ruff format . && ruff check . && mypy src && pytest'`
  - Passed: Ruff, strict mypy, and 10 tests.
- `nix flake check -L`
  - Passed all x86_64-linux formatting, lint, typing, unit, and Home Manager
    module checks.
- `nix flake check --all-systems --no-build`
  - Passed output evaluation for x86_64-linux and aarch64-linux.
- `nix build .#ai-tools-api -L`
  - Passed. Built the uv2nix application, patched Piper, Nix launcher, adjacent
    voice assets, and fixed model references. The first stale two-line patch
    applied at the wrong location; it was replaced with a full-context patch and
    the clean rebuild had no `IndentationError` or failed hunk.
- Packaged Piper adapter diagnosis with `Hello my friend`
  - Passed without playback: exit 0, 48,172 WAV bytes, one channel, 22,050 Hz,
    and 24,064 frames.
- `nix shell nixpkgs#actionlint -c actionlint`
  - Passed both GitHub workflow files.
- Real Whisper and Piper inference were not run because they are third-party
  behavior and this repository uses injected mocks for its own tests.

## Deferred

- Host deployment remains deferred until a concrete private target is selected.
- A GitHub repository and releases remain deferred. Workflows are present but
  dormant.
