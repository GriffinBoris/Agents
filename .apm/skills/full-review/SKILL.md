---
name: full-review
description: Perform a comprehensive, evidence-backed review of a declared scope. Use when explicitly asked for a full, comprehensive, or deep review of a branch diff, selected files, folder, app, feature, route, module, workflow, guidance package, or repository; do not trigger for ordinary implementation or a quick question about one issue.
---

# Full Review

## Scope

- Review the scope named by the user. If no scope is supplied, review the current branch changes.
- Treat the work as one integrated review rather than a generic command chooser or separate stack-by-stack reports.
- Follow the `Review Reporting` and `Code Review Practices` sections of the engineering baseline.
- Keep the review read-only unless the user also asks to address findings.

## Workflow

1. State the exact scope and identify skipped files, blind spots, and lightly checked areas.
2. Identify the concrete concerns before loading detailed guidance or examples.
3. Load the consuming repository's `project-architecture` skill and every language, framework, or domain skill that owns an in-scope concern.
4. When the scope is broad, unfamiliar, or concept-based, map the relevant structure, responsibilities, dependencies, and data flow before judging it.
5. Inspect every declared in-scope file or changed area and enough surrounding code to understand its contracts and closest local patterns.
6. Apply every relevant specialized audit and produce one final report using the baseline review contract.

## Audit Selection

- Load `architecture-audit` for file, folder, module, responsibility, boundary, layering, or code-shape concerns.
- Load `backend-homogeneity-audit` for backend consistency concerns.
- Load `frontend-homogeneity-audit` for frontend consistency concerns.
- Load multiple audits when the scope contains multiple distinct concerns; do not load an audit merely because its stack exists in the repository.

## Completion Checklist

- Every declared in-scope area was reviewed or identified as a blind spot.
- Applicable guidance, examples, local patterns, and audit criteria were recorded as required by the baseline.
- Every verified finding was reported with evidence, or the report explicitly states that none were found.
- Verification performed and not performed is clear.
- No code was changed unless the user requested fixes.
