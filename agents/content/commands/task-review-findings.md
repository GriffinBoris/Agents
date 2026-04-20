---
kind: command
role: opencode-command
description: Review a scoped area from the dumped task-review context and write all findings to a repeatable docs artifact
---

Read the dumped `task-review` context artifact and perform the actual scoped review.

Scope comes from `$ARGUMENTS`.
If no explicit scope is provided, use the `current-branch-diff` scope.

Input mode:
- `$ARGUMENTS` may be either:
  - an explicit scope, or
  - a path to `docs/task-review/<scope-slug>/task-review-context.md`
- if a context artifact path is provided, use that file as the source of truth and derive the scope slug from its parent folder

Artifact rules:
- use the same scope label and slug rules as `task-review-context`
- require `docs/task-review/<scope-slug>/task-review-context.md`
- create or update `docs/task-review/<scope-slug>/task-review-findings.md`

Read these before judging the scope:
- `docs/task-review/<scope-slug>/task-review-context.md`
- `agents/guidance/guidance.md`
- relevant language, framework, and project guidance
- nearby named examples under `agents/guidance/**/examples/`
- `agents/reference/review/architecture-rubric.md`
- `agents/reference/antipatterns/overview.md`

Use the full-review mindset:
- inspect every in-scope file or changed area
- compare the scoped code to the relevant guidance rules
- compare the scoped code to the matching examples captured in the context file
- compare structure and organization to the closest real repo patterns
- list every verifiable in-scope deviation, not just a curated sample

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
- every verified in-scope guidance deviation
- every scoped anti-guided or example-divergent shape you can verify
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
Do not omit lower-severity in-scope deviations because higher-severity findings exist.

Keep the artifact under `docs/task-review/` as a temporary working review document.

In the final response, return the exact written findings artifact path.
