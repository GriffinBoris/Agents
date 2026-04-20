---
kind: skill
name: architecture-audit
description: >
  Audit file structure, folder structure, module boundaries, code structure,
  readability, and clean architecture.
---

# Architecture Audit

## When to use
- Reviewing a PR or diff that changes structure, layering, or responsibilities
- Checking whether a module, route, service, or workflow has become too complex
- Reviewing whether files, folders, packages, or feature boundaries are organized clearly
- Reviewing whether function, class, and module shape stays readable and proportional to the problem
- Preparing a refactor plan
- Doing a final readability and maintainability pass before merge

## Boundary
- Use this as the primary structure and readability audit for files, folders, modules, and code shape.
- Pair it with backend or frontend homogeneity audits when stack-specific patterns matter.
- Use `full-review` for the final comprehensive scoped review workflow.

## Read first
- `agents/guidance/guidance.md`
- relevant `agents/guidance/languages/<name>/guidance.md`
- relevant `agents/guidance/frameworks/<name>/guidance.md`
- `agents/guidance/project/guidance.md`
- nearby example docs in `agents/guidance/**/examples/`
- `agents/reference/review/architecture-rubric.md`

## Goals
- Judge the code against the modular guidance tree, not old monolithic docs
- Compare new structure to the closest existing in-repo pattern before calling it a problem
- Report all verifiable in-scope guidance deviations, not just the top few
- Prefer the simplest fix that restores clarity, boundaries, and consistency

## What to inspect

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

## Audit workflow

### 1. State the scope
- Name the exact scope: diff, files, folder, feature, route, app, or full repo
- List anything skipped or only lightly checked

### 2. Build the review map
For each applicable guidance or example source, record:
- file path
- why it applies
- verdict: `matched`, `partially_matched`, `not_matched`, or `not_applicable`

### 3. Inspect the structure
- Check file and folder layout for clarity and scope fit
- Check file and module responsibilities
- Check function, method, class, and public API shape
- Check whether boundaries between UI, transport, domain, persistence, and integrations stay clear
- Check whether names, control flow, and state changes stay readable
- Check whether abstractions are justified by real reuse

### 4. Compare to established patterns
- Find the closest existing implementation in the repo
- Prefer proven local patterns over invented structure
- Treat unexplained deviation from guidance or examples as a finding

### 5. Record findings completely
- List every verifiable guidance deviation in scope
- Tie each finding to a file, a rule or example, and the simplest fix
- If no deviations are found, say that explicitly

## Output

### Scope
- reviewed area
- skipped or lightly checked areas

### Structure Map
- file and folder layout notes
- module or boundary map where helpful

### Guidance Reviewed
- applicable guidance and example files with verdicts

### Findings
- severity
- file reference
- issue
- violated rule, example, or pattern
- simplest fix

### Action Plan
- 1 to 3 quick improvements
- any larger follow-up refactor worth doing later

### Verification And Blind Spots
- what was verified
- what was not verified
- any blind spots affecting confidence

## Living document note
- If you discover a durable rule, example gap, or better review heuristic, update the authored modular tree under `agents/guidance/`, `agents/reference/`, or `agents/content/` instead of generated output.
