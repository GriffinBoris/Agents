---
name: guidance-review
description: Audit a codebase against one named guidance document and, when requested, correct every verified deviation. Use when the user supplies or identifies a specific guidance file and asks for a deep compliance audit, migration, or remediation; do not trigger for a general code review without a governing document.
---

# Guidance Review

## Scope

- Treat the selected guidance document's central idea as the audit subject.
- Follow the `Review Reporting` and `Code Review Practices` sections of the engineering baseline.
- Audit read-only when the user asks only for findings. Apply corrections when the user asks to correct, migrate, enforce, or bring the code into compliance.
- If no guidance document can be identified from the request or repository context, ask for its path before continuing.

## Workflow

1. Read the complete selected guidance document and extract its subject, concrete rules, required patterns, constraints, anti-patterns, and verification expectations.
2. Search broadly for every related implementation, usage, example, and near-miss. Include all relevant surfaces for the active stack, such as models, endpoints, services, tasks, stores, routes, components, tests, commands, middleware, and shared utilities.
3. Build a compliance report that records matching, partial, and non-matching files. Tie each deviation to the exact guidance rule and explain why it matters.
4. When remediation is in scope, apply the simplest appropriate fix without changing unrelated code.
5. Add or update tests when the guidance governs behavior, scoping, permissions, data contracts, routing, lifecycle rules, or another enforceable contract.
6. Run the repository's relevant linters, static checks, targeted tests, and any additional minimal verification required by the guidance.
7. Return one final report covering the subject, extracted rules, files audited, findings before changes, changes made, verification, and remaining gaps.

## Boundaries

- Preserve the selected guidance's purpose and architectural boundaries while following established repository patterns.
- Record a compliant file only after checking it; do not infer compliance from its name or location.
- Report every verified occurrence in scope, not only representative examples.
- Do not weaken a guidance rule merely to avoid an in-scope refactor.
- Do not change code when the request is explicitly read-only.

## Completion Checklist

- The governing document and audit subject are explicit.
- Every relevant surface was searched and classified.
- Each finding cites the governing rule and source evidence.
- Authorized corrections and contract-level tests are complete.
- Verification and remaining gaps are reported.
