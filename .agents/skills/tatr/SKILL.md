---
name: tatr
description: Create and maintain repository Markdown tasks for tracked work.
---

# Tatr

Tasks live at `tasks/<YYYYMMDD-HHMMSS>/TASK.md`.

```bash
tatr -r . new "Title" -p 100 -t api
tatr -r . ls --sort priority
tatr -r . edit <id> --status IN_PROGRESS
```

Use statuses `OPEN`, `IN_PROGRESS`, and `CLOSED`. After creation, edit the task
body directly. Record contract and package decisions, deferred work, and exact
verification commands with outcomes. Close only after required checks pass.
