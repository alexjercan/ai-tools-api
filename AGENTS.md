# AGENTS.md

## Architecture

- `src/ai_tools_api` contains the typed HTTP API, validation, backend adapters,
  process supervision, and command entry point.
- `tests` uses injected fake backends. Ordinary tests need no model, GPU, audio
  device, or network.
- `nix` owns packages, pinned models, the Home Manager module, and Nix checks.
- `docs` owns durable API and operations documentation. Keep `README.md` short.

## Workflow

- Work directly on `master`. Track substantial work in `tasks/<id>/TASK.md`.
- Record decisions and verification evidence in the task.
- Make focused commits. Do not add remotes or generated build outputs.
- Use Pair for decisions and continue mechanical work without confirmation.

## Python

- Support Python 3.11 or newer. Use complete type hints.
- Keep handlers thin. Separate validation, adapters, WAV parsing, and process
  ownership.
- Run `ruff format --check .`, `ruff check .`, `mypy src`, and `pytest`.
- Never use a shell for child processes. Inject fake backends in tests.

## Nix

- The flake owns executable packages, model fetches, checks, and deployment.
- Keep URLs and hashes exact. Do not use impure path discovery.
- Support Linux only unless a tested change expands support.
- Run `nix flake check -L` and `nix build .#ai-tools-api` before completion.

## Processes and bounds

- Record child objects and signal only those children. Never use broad process
  matching.
- Bound input, output, concurrency, startup, request, and shutdown time.
- Reject known-invalid work before a backend call. Clean temporary files.
- Do not log speech text, audio, stderr, commands, paths, or model internals.

## Tests and documentation

- Add behavior with focused deterministic tests. Real inference is opt-in.
- Keep exactly the documented public routes unless a tracked contract decision
  changes scope.
- Document all defaults and security boundaries under `docs`.
- Preserve user authorship. Do not add attribution trailers.
