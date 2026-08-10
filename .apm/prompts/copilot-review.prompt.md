---
description: Review Copilot pull-request comments for a provided PR URL.
input: [pr_url]
---

Review Copilot PR comments for `${input:pr_url}`.

Use `gh api repos/<org>/<repo>/pulls/<id>/comments` to fetch inline review comments.
Load `review-workflows` and judge each suggestion using its shared evidence and reporting contract.

Use `architecture-audit`, `backend-homogeneity-audit`, `frontend-homogeneity-audit`, or `context-gatherer` only when the comment touches the concern that skill owns.

For each Copilot suggestion, decide:
- required change
- optional improvement
- no action

Report the decision and evidence for each suggestion, then include any additional in-scope findings required by the shared review contract.
