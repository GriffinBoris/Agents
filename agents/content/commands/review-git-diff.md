---
kind: command
role: opencode-command
description: Review git diff compared to origin/main
---

Git diff compared to origin/main
!git --no-pager diff origin/main

Review the git diff above and familiarize yourself with the changes.
Gather any additional context you may need to understand the changes.

Use `context-gatherer`, `architecture-audit`, `backend-homogeneity-audit`, and `frontend-homogeneity-audit` when they help cover the diff well.

In your final review:
- state the diff scope clearly
- list the guidance and examples reviewed
- list all verifiable guidance deviations within the diff scope, or explicitly state that none were found
- report verification status and blind spots
