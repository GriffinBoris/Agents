---
kind: command
role: opencode-command
description: Review Copilot PR comments for a provided PR URL
---

Review Copilot PR comments for the provided PR URL.

Use `gh api repos/<org>/<repo>/pulls/<id>/comments` to fetch inline review comments.
Judge each suggestion against the modular guidance tree and nearby examples:
- `agents/guidance/guidance.md`
- relevant language, framework, and project guidance
- nearby named examples under `agents/guidance/**/examples/`

Use `architecture-audit`, `backend-homogeneity-audit`, `frontend-homogeneity-audit`, and `context-gatherer` when the comment touches structure, stack conventions, or missing context.

For each Copilot suggestion, decide:
- required change
- optional improvement
- no action

If you identify in-scope guidance deviations while evaluating the comments, list them all or explicitly state that none were found.
