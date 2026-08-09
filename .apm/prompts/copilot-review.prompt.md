---
description: Review Copilot pull-request comments for a provided PR URL.
input: [pr_url]
---

Review Copilot PR comments for `${input:pr_url}`.

Use `gh api repos/<org>/<repo>/pulls/<id>/comments` to fetch inline review comments.
Judge each suggestion against the modular guidance tree and nearby examples:
- `.apm/instructions/engineering-baseline.instructions.md`
- relevant language, framework, and project guidance
- matching examples under the relevant guidance skill's `references/examples/` directory

Use `architecture-audit`, `backend-homogeneity-audit`, `frontend-homogeneity-audit`, and `context-gatherer` when the comment touches structure, stack conventions, or missing context.

For each Copilot suggestion, decide:
- required change
- optional improvement
- no action

If you identify in-scope guidance deviations while evaluating the comments, list them all or explicitly state that none were found.
