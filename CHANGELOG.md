# Changelog

All notable user-facing changes to ai-tools-api.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Releases are
immutable `vX.Y.Z` tags; see [RELEASE.md](RELEASE.md) for the process.

## [Unreleased]

### Added

- Strict OpenAI-compatible chat completions with bounded JSON and SSE responses.
- An owned loopback llama.cpp model router with pinned Qwen and Gemma models.

## [0.1.1] - 2026-08-30

### Fixed

- Home Manager user services can enter their protected runtime working
  directories.

## [0.1.0] - 2026-08-30

### Added

- Bounded OpenAI-compatible speech transcription and synthesis routes.
- A Nix runtime that composes the API with a pinned Whisper server, patched
  Piper executable, and adjacent pinned Piper voice assets.
- A Home Manager module with separate hardened API and loopback Whisper user
  services.
- Deterministic Python, Nix package, and Home Manager module checks.

[Unreleased]: https://github.com/alexjercan/ai-tools-api/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/alexjercan/ai-tools-api/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/alexjercan/ai-tools-api/releases/tag/v0.1.0
