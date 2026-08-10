---
description: Review the current git diff compared to origin/main.
---

Run `git --no-pager diff origin/main` and review its output.

Load `review-workflows` and use its shared scope, applicability-map, evidence, findings, and output contract for the diff.

Use `context-gatherer`, `architecture-audit`, `backend-homogeneity-audit`, or `frontend-homogeneity-audit` only when the diff includes the concern that skill owns.

Gather enough local context to understand every changed area, then return the review using the shared output contract.
