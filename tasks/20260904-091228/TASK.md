# Release backend timeout fix

- STATUS: CLOSED
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

Publication and deployment:

- Release commit and annotated `v0.2.1` tag target
  `f05191a507c4ac834d90ac67ef5da03bf1f424aa`.
- Pushed `master` and only the `v0.2.1` tag.
- Branch check passed:
  https://github.com/alexjercan/ai-tools-api/actions/runs/33843489304
- Tag check and source release passed:
  https://github.com/alexjercan/ai-tools-api/actions/runs/33843492066
- Published stable source release:
  https://github.com/alexjercan/ai-tools-api/releases/tag/v0.2.1
- `nix.dotfiles` commit `606c992` pins v0.2.1 and was pushed to `master`.
- Home Manager activation completed. The active API uses 0.2.1, and a live
  non-streaming Gemma request that exceeded five seconds returned HTTP 200.

