# Release backend timeout fix

- STATUS: OPEN
- PRIORITY: 100
- TAGS: release

## Scope

Release the corrected LLM backend timeout behavior as version 0.2.1. Push
`master` and the immutable release tag, verify GitHub workflows, pin the release
in `~/personal/nix.dotfiles`, and activate the Home Manager generation.

## Decisions

- Use patch release 0.2.1 because the public API contract is unchanged.
- Align the package and module `__version__` values.
- Keep the existing v0.2.0 runtime and model packaging decisions.

## Verification

Pre-release checks:

- `uv lock --offline` updated project metadata to 0.2.1.
- `nix shell nixpkgs#actionlint -c actionlint` passed.
- `uv lock --check`, `ruff format --check .`, `ruff check .`, `mypy src`, and
  `pytest` passed; 24 tests passed with one known upstream warning.
- `nix flake check -L` passed all eight checks on x86_64-linux.
- `nix build .#ai-tools-api -L` passed.
- `git diff --check` passed.

Publication and deployment are pending.

