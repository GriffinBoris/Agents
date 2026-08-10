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

Load `review-workflows` and follow its shared scope, applicability-map, evidence, findings, and output contract. Treat this command as one integrated review of the in-scope material, not a generic command chooser or a stack-by-stack checklist.

Use these skills as relevant:
- `architecture-audit`
- `backend-homogeneity-audit`
- `frontend-homogeneity-audit`
- `context-gatherer`

Use `context-gatherer` first when the scope is broad, unfamiliar, or concept-based.
Use `architecture-audit` for file, folder, module, and code-structure review.
Use the backend or frontend homogeneity audits when those stacks are in scope.

Inspect every declared in-scope file or changed area. Apply all specialized audit criteria that match the concerns, then produce one final report using the `review-workflows` output contract.
