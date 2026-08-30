# Prepare tagged source releases

- STATUS: CLOSED
- PRIORITY: 100
- TAGS: release

## Scope

Document the 0.1.0 release and add tag-driven source release automation for
Nix consumers.

## Decisions

- Publish immutable stable `vX.Y.Z` tags and source-only GitHub Releases.
- Keep the flake as the consumer interface. Do not upload Python distributions
  or Nix build outputs as release assets.
- Reuse the branch check workflow from the tag workflow, including the Nix
  package build.
- Require the tag version to equal `project.version` in `pyproject.toml`.

## Verification

- `uv run ruff format --check . && uv run ruff check . && uv run mypy src && uv run pytest`
  - Passed formatting, lint, strict typing, and 10 tests. Pytest reported one
    upstream Starlette `httpx` deprecation warning.
- `nix shell nixpkgs#actionlint -c actionlint`
  - Passed both workflow files.
- `nix flake check -L`
  - Passed all x86_64-linux source and Home Manager checks.
- `nix build .#ai-tools-api`
  - Passed the complete Nix package build.
- `git diff --check`
  - Passed.

