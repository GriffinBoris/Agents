---
description: Review a scoped area from saved task-review context and write all findings to a repeatable artifact.
input: [scope]
---

Read the dumped `task-review` context artifact and perform the actual scoped review.

Scope comes from `${input:scope}`.
If no explicit scope is provided, use the `current-branch-diff` scope.

Input mode:
- `${input:scope}` may be either:
  - an explicit scope, or
  - a path to `docs/task-review/<scope-slug>/task-review-context.md`
- if a context artifact path is provided, use that file as the source of truth and derive the scope slug from its parent folder

Artifact rules:
- use the same scope label and slug rules as `task-review-context`
- require `docs/task-review/<scope-slug>/task-review-context.md`
- create or update `docs/task-review/<scope-slug>/task-review-findings.md`

Load `review-workflows` and follow its shared scope, applicability-map, evidence, findings, and output contract. Read these workflow inputs and supporting review references before judging the scope:
- `docs/task-review/<scope-slug>/task-review-context.md`
- `.apm/skills/review-workflows/references/architecture-rubric.md`
- `.apm/skills/review-workflows/references/antipatterns.md`

Inspect every scoped file or changed area and use the matching examples captured in the context artifact as the initial applicability set. Add another example only when the review exposes a concrete concern the context artifact missed.

Use these audits when relevant:
- `architecture-audit`
- `backend-homogeneity-audit`
- `frontend-homogeneity-audit`
- `context-gatherer` again only if a missing context gap blocks the review

`task-review-findings.md` must include:
- scope summary
- reviewed context artifact path
- guidance files reviewed
- example files reviewed
- review map summary for the scoped files or areas
- findings ordered by severity
- issue ids such as `TR-001`
- for each issue:
  - severity
  - bucket
  - concrete file references
  - short issue statement
  - local context needed to understand the issue
  - violated guidance, example, or anti-pattern reference
  - simplest fix direction
- verification status and blind spots

Use these issue buckets when relevant:
- correctness
- security-and-scoping
- architecture-and-boundaries
- homogeneity-and-consistency
- testing-and-verification
- docs-guidance-and-example-drift
- tooling-and-metadata-gaps

If no verified issues are found, say so explicitly.

Keep the artifact under `docs/task-review/` as a temporary working review document.

In the final response, return the exact written findings artifact path.
