# Fix user service runtime directory isolation

- STATUS: CLOSED
- PRIORITY: 100
- TAGS: nix, systemd

## Problem

The deployed Home Manager units failed with `status=200/CHDIR`. Both combined a working directory below the user runtime directory with `ProtectHome=true`:

```text
RuntimeDirectory=ai-tools-api
WorkingDirectory=%t/ai-tools-api
ProtectHome=true
```

For a user service, `%t` is below `/run/user`. The `true` protection mode hides `/run/user` inside the service mount namespace, including the runtime directory systemd created for the unit.

## Fix

Use `ProtectHome=tmpfs` for both the API and private Whisper units. This keeps home and other user runtime contents hidden while systemd exposes each declared `RuntimeDirectory` inside the namespace.

The Home Manager module evaluation check now asserts this mode for both generated units.

## Verification

- Minimal live user units reproduced the failure with `ProtectHome=true` and passed with `ProtectHome=tmpfs` while using `RuntimeDirectory` as `WorkingDirectory`.
- `nix build .#checks.x86_64-linux.module-evaluation --no-link` passed.
- `nix flake check -L` passed formatting, lint, strict typing, 10 unit tests, module evaluation, and package evaluation.
- `nix build .#ai-tools-api --no-link` passed.
- `git diff --check` passed.

