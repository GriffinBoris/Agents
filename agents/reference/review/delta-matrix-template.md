---
id: reference-review-delta-matrix-template
title: Review Delta Matrix Template
description: Template for mapping discovered review rules against existing guidance.
kind: reference
scope: global
name: review-delta-matrix-template
tags:
  - reference
  - review
  - template
applies_to: []
status: active
order: 3
---

# Review Delta Matrix Template

```markdown
| Rule / Pattern | Evidence Repo(s) | Current Location | Status | Proposed Destination | Action |
|---|---|---|---|---|---|
| [Rule name] | [Where discovered] | [File if it exists] | match / partial / missing | [Target file] | keep / add / clarify |
```

## Usage Notes

- Use this matrix during guidance migration and cross-repo audits.
- Mark `partial` when a rule exists but is incomplete, duplicated, or misplaced.
- Prefer one destination per rule so guidance ownership stays clear.
- When using this during review prep, make sure every applicable in-scope rule or example ends up accounted for as `match`, `partial`, or `missing` rather than leaving silent gaps.
