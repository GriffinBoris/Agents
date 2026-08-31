---
name: review-git-diff
description: Review the current branch diff against origin/main using repository guidance and local implementation evidence. Use when explicitly asked to review the git diff, current changes, or branch changes before merge; do not trigger for a full-repository audit or when the user asks to implement fixes instead of reviewing.
---

# Git Diff Review

## Scope

- Review `git --no-pager diff origin/main` by default.
- If `origin/main` is unavailable or the user names another base, state and use the resolved comparison base.
- Follow the `Review Reporting` and `Code Review Practices` sections of the engineering baseline.
- Keep the review read-only unless the user separately asks to address findings.

## Workflow

1. Inspect repository status and the complete diff against the comparison base.
2. Read enough surrounding code, tests, and local guidance to understand every changed area and its contracts.
3. Load the language, framework, domain, and project skills that own concrete concerns in the diff.
4. Load `architecture-audit`, `backend-homogeneity-audit`, or `frontend-homogeneity-audit` only when the diff includes the concern that audit owns.
5. Report every verified finding using the baseline review contract, or state explicitly that no verified findings were found.

## Completion Checklist

- The comparison base and reviewed diff are explicit.
- Every changed area was inspected with enough local context.
- Findings distinguish verified defects from preferences and unverified suspicions.
- Verification and blind spots are reported.
- No code was changed unless the user requested fixes.
