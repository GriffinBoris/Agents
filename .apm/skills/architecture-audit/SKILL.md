---
name: architecture-audit
description: Audit file, folder, module, responsibility, layering, readability, and maintainability choices. Use when explicitly reviewing structural changes, assessing complexity, planning a refactor, or performing a final architecture pass; do not trigger for ordinary implementation.
---

# Architecture Audit

## Scope

- Evaluate structure, responsibilities, boundaries, readability, and proportionality against applicable guidance and the closest local patterns.
- Produce evidence-backed findings or a focused refactor plan without expanding the review beyond its declared scope.

### Boundaries

- Use this as the primary structure and readability audit for files, folders, modules, and code shape.
- Pair it with backend or frontend homogeneity audits when stack-specific patterns matter.
- Follow the review reporting and code-review practices in the [engineering baseline](../../instructions/engineering-baseline.instructions.md); the criteria and output below are additions specific to architecture.

## Workflow

1. Apply the baseline review contract and select the architecture rubric.
2. Inspect the file and folder layout, responsibilities, public surface, control flow, state changes, abstractions, dependency direction, and boundaries between UI, transport, domain, persistence, and integrations.
3. Add the architecture-specific structure map and action plan to the baseline review output.

## Reference Selection

- [Architecture rubric](references/architecture-rubric.md)

## Review Criteria

### File and folder structure

- whether responsibilities are split across the right files and folders
- whether names describe purpose clearly
- whether a feature is flat, feature-foldered, or over-nested for its real size
- whether growth signals suggest a split or consolidation

### Module and code structure

- whether each module has one clear responsibility
- whether functions, methods, and classes are sized and named clearly
- whether public surface area is justified by real callers
- whether control flow, state changes, and side effects stay obvious

### Boundaries and layering

- whether UI, transport, domain, persistence, and integration boundaries stay clear
- whether dependencies point the right direction
- whether helpers and abstractions are justified by real reuse

## Output

In addition to the baseline review output, include:

### Structure Map

- file and folder layout notes
- module or boundary map where helpful

### Action Plan

- 1 to 3 quick improvements
- any larger follow-up refactor worth doing later

## Completion Checklist

- File, folder, module, responsibility, boundary, and public-surface concerns were covered where applicable.
- The structure map makes ownership and dependency direction understandable.
- Suggested refactors are proportionate to the verified problem and declared scope.
