# Release llama.cpp chat completions

- STATUS: OPEN
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

Record pushed revisions, workflow runs, and release URL after publication.

