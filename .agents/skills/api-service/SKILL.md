---
name: api-service
description: Implement bounded speech API behavior and focused backend tests.
---

# API service

1. Read `docs/api.md`, `docs/configuration.md`, and the active task.
2. Change typed validation or adapters before changing thin route handlers.
3. Reject content type, declared size, fields, and text before acquiring a
   concurrency slot or starting backend work.
4. Keep client errors stable and operational details only in sanitized logs.
5. Use command arrays and injected fakes. Test timeout, cancellation, overload,
   malformed output, and information leakage.
6. Run `ruff check .`, `mypy src`, and the smallest relevant pytest file, then
   run all Python checks before completion.
