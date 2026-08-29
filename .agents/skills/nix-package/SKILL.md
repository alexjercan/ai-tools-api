---
name: nix-package
description: Maintain flake runtime composition, pinned models, modules, and Nix checks.
---

# Nix package

1. Read `flake.nix`, `nix/module.nix`, deployment docs, and the active task.
2. Keep executable and model paths in the store and pass trusted absolute paths
   through the wrapper. Fetch models only by exact URL and hash.
3. Test package closure for Whisper, Piper, assets, and Python dependencies.
4. Evaluate the Home Manager module disabled and enabled. Keep internal Whisper
   on loopback and preserve focused systemd hardening.
5. Keep real model inference opt-in. Run `nix flake check -L` and
   `nix build .#ai-tools-api` after cheaper evaluation checks.
