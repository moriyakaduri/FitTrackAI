---
name: fittrack-safe-change
description: >-
  Guide a small, safe change to FitTrackAI. Use when editing this project,
  making a focused bugfix or tiny feature, or when the user mentions
  fittrack-safe-change, a safe change, or a small patch.
---

# FitTrackAI safe change

When making a small change to this project, follow this workflow.

1. Inspect the relevant existing code before editing.
2. Make the smallest change needed.
3. Preserve the existing MVP / FastAPI architecture.
4. Never expose or commit secrets or `.env`.
5. Avoid unrelated refactoring.
6. Validate the affected functionality after the change.
7. Check git diff/status before finishing.
8. Create a focused commit only after validation.

Do not move files, add layers, or rewrite architecture unless the user asked for that change.
Do not push unless the user asked to push.
