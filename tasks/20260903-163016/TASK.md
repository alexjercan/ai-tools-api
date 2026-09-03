# Release llama.cpp chat completions

- STATUS: CLOSED
- PRIORITY: 100
- TAGS: release

## Scope

Release the bounded llama.cpp chat completion API as version 0.2.0. Push
`master` and the immutable release tag, then verify branch and release workflows.

## Packaging decision

The complete runtime closure is 61.7 GiB because it contains both pinned Q8
models. Verify that closure locally. CI builds `ai-tools-api-core` so a hosted
runner does not need a second 60 GiB model download. `nix flake check` still
evaluates the complete package and all fixed model references.

## Verification

Pre-release checks on 2026-09-03:

- `uv lock --offline`: updated locked project metadata to 0.2.0.
- `actionlint`: passed both workflows.
- `ruff format --check .`, `ruff check .`, `mypy src`, and `pytest`: passed;
  22 tests passed with one upstream Starlette deprecation warning.
- `nix flake check -L`: passed on x86_64-linux.
- `nix build .#ai-tools-api -L`: passed with both pinned Q8 models.
- `git diff --check`: passed.

Publication:

- Release commit and annotated `v0.2.0` tag target
  `b05e0b4bf94337d7bb74cb17aef323d1ce963464`.
- Pushed `master`, then pushed only `v0.2.0`.
- Branch check passed: https://github.com/alexjercan/ai-tools-api/actions/runs/33761637957
- Tag check and source release passed: https://github.com/alexjercan/ai-tools-api/actions/runs/33761642222
- Published stable source release:
  https://github.com/alexjercan/ai-tools-api/releases/tag/v0.2.0

