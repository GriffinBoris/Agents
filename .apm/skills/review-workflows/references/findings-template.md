---
id: reference-review-findings-template
title: Review Findings Template
description: Template for recording architecture or code-review findings.
kind: reference
scope: global
name: review-findings-template
tags:
  - reference
  - review
  - template
applies_to: []
status: active
order: 2
---

# Review Findings Template

```markdown
## [Repository Name]

### Stack Summary
[One paragraph covering language, framework, purpose, and deployment model]

### Critical Bugs
| Bug | Location | Severity |
|---|---|---|

### What Is Good
- [Specific architecture decisions or code-quality strengths]

### What Is Bad
- [Specific problems with file paths and line numbers]

### Guidance Deviations In Scope
- [Every verified guidance deviation in scope, with rule or example source]
- [If none, say "No verified guidance deviations found in reviewed scope"]

### Candidate Rules To Promote
- [Patterns discovered that should become reusable guidance]
```

## Usage Notes

- Cite file paths and line numbers for every finding.
- Keep strengths concrete, not generic praise.
- Separate correctness bugs from maintainability observations.
- Do not omit in-scope guidance deviations just because they are low severity; list them or explicitly record that none were found.
