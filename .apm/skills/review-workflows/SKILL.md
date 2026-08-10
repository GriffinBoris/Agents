---
name: review-workflows
description: Use when performing a structured code or guidance review and needing the shared review rubric, finding template, delta matrix, or anti-pattern catalog.
---

# Review Workflows

## Scope

- Provide the shared scope, evidence, applicability, findings, and reporting contract for structured reviews.
- Keep supporting review material lazy and load only what the concrete review concerns require.

### Boundaries

- Applicable baseline, language, framework, and project guidance remains the source of truth. Review references organize the evaluation; they do not replace the owning guidance.
- Judge against the authored modular guidance tree, not generated or preserved legacy aggregate documents.
- Use the specialized architecture, backend, or frontend audit skill for its additional criteria. Use the `full-review` command when one review must integrate multiple concerns.

## Workflow

1. State the exact scope: diff, files, folder, feature, route, app, module, concept, or full repository. List skipped or lightly checked areas.
2. Identify the concrete concerns in scope, then load the owning guidance, the consumer's `project-architecture` skill, and the closest established local implementations.
3. Build an applicability map for each guidance or example source actually reviewed:
   - file path
   - concern it governs
   - why it applies
   - verdict: `matched`, `partially_matched`, `not_matched`, or `not_applicable`
4. Inspect the complete declared scope and compare each area to the applicable rules, examples, and established local patterns.
5. Record every verifiable in-scope deviation with evidence, or explicitly state that none were found. If one issue occurs repeatedly, enumerate the audited occurrences or provide the full occurrence list.
6. Use the appropriate output template when the review needs a findings report or delta comparison.

## Example Applicability

- Start with the owning skill's example-selection routing. Discover additional examples only when a concrete in-scope concern is not covered there.
- Use the filename, H1, `Scenario`, and heading list to decide whether an example teaches the same concern; sharing a broad stack is not enough.
- For long examples, inspect the scenario and headings first, then read only the relevant sections.
- Review every example needed to cover distinct in-scope concerns, but do not load or list unrelated examples preemptively.
- Keep reviewed examples in the applicability map even when they produced no findings.

## Reference Selection

- Load [architecture-rubric.md](references/architecture-rubric.md) for structure and architecture reviews.
- Load [findings-template.md](references/findings-template.md) when preparing a complete findings report.
- Load [delta-matrix-template.md](references/delta-matrix-template.md) when comparing a change against the expected pattern.
- Load [antipatterns.md](references/antipatterns.md) when checking for known discouraged shapes.

## Review Criteria

- Base findings on actual source evidence, not assumptions.
- Compare to the closest local implementation before treating a difference as a problem.
- Distinguish verified deviations from preferences, intentional exceptions, and unverified suspicions.
- Prefer the simplest fix that restores correctness, clarity, boundaries, and consistency without expanding scope.

## Output Contract

- Scope and any skipped or lightly checked areas.
- Guidance and example applicability map.
- Findings ordered by severity. Each finding includes a concrete file reference, evidence, the applicable rule/example/pattern, and the simplest appropriate fix.
- Verification performed, verification not performed, and blind spots affecting confidence.
- An explicit no-findings statement when no verifiable deviations were found.
- Use the findings template for a complete review report and the delta matrix when mapping expected and actual patterns.

## Completion Checklist

- Applicable guidance was loaded before supporting review references.
- Only task-relevant references were loaded.
- Every declared in-scope area was evaluated or recorded as a blind spot.
- Every verifiable in-scope deviation was reported, or the absence of findings was stated explicitly.
