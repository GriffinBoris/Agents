---
name: review-workflows
description: Use when performing a structured code or guidance review and needing the shared review rubric, finding template, delta matrix, or anti-pattern catalog.
---

# Review Workflows

## Scope

- Use the relevant global, language, framework, and project guidance before evaluating a change.
- Keep supporting review material lazy and load only what the review requires.

### Boundaries

- Do not treat a review reference as a replacement for the applicable guidance skills.
- Use the specialized architecture, backend, or frontend audit skill when that workflow matches the review.

## Workflow

1. State the exact review scope and any blind spots.
2. Load the applicable guidance skills.
3. Select only the supporting references needed for the review.
4. Evaluate the complete scope and report every verifiable deviation or explicitly state that none were found.
5. Use the appropriate output template when the review needs structured findings or a delta comparison.

## Reference Selection

- Load [architecture-rubric.md](references/architecture-rubric.md) for structure and architecture reviews.
- Load [findings-template.md](references/findings-template.md) when preparing a complete findings report.
- Load [delta-matrix-template.md](references/delta-matrix-template.md) when comparing a change against the expected pattern.
- Load [antipatterns.md](references/antipatterns.md) when checking for known discouraged shapes.

## Review Criteria

- Compare the change against every applicable rule, example, and established local pattern.
- Distinguish verified deviations from preferences and unverified suspicions.
- Tie findings to concrete files, applicable guidance, and the simplest appropriate fix.

## Output

- Use the findings template for a complete review report.
- Use the delta matrix when mapping expected and actual patterns.
- Include scope, skipped areas, findings, verification, and blind spots.

## Completion Checklist

- Applicable guidance was loaded before supporting review references.
- Only task-relevant references were loaded.
- Every verifiable in-scope deviation was reported, or the absence of findings was stated explicitly.
