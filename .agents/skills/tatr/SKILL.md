---
name: tatr
description: Create and maintain repository Markdown tasks for tracked work.
---

# Tatr

Tasks live at `tasks/<YYYYMMDD-HHMMSS>/TASK.md`.

```bash
tatr -r . new "Title" -p 100 -t api
tatr -r . ls --sort priority
tatr -r . edit <id> --status CLOSED
```

Use statuses `OPEN` and `CLOSED`. After creation, edit the task
body directly. Record contract and package decisions, deferred work, and exact
verification commands with outcomes. Close only after required checks pass.
