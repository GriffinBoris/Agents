---
description: Perform a comprehensive scoped review of code or guidance in the repository.
input: [scope]
---

Perform a comprehensive scoped review.

Scope comes from `${input:scope}`.
If no scope is provided, review the current branch changes.

Supported scopes include:
- current branch diff
- selected files
- a folder, app, feature, route, or module
- a concept or workflow across multiple files
- a guidance package, examples folder, or selected guidance files

Follow the `Review Reporting` and `Code Review Practices` sections of the engineering baseline. Treat this command as one integrated review of the in-scope material, not a generic command chooser or a stack-by-stack checklist.

Use these skills as relevant:
- `architecture-audit`
- `backend-homogeneity-audit`
- `frontend-homogeneity-audit`

When the scope is broad, unfamiliar, or concept-based, map the relevant structure, responsibilities, and data flow before judging it.
Use `architecture-audit` for file, folder, module, and code-structure review.
Use the backend or frontend homogeneity audits when those stacks are in scope.

Inspect every declared in-scope file or changed area. Apply all specialized audit criteria that match the concerns, then produce one final report using the baseline review contract.
