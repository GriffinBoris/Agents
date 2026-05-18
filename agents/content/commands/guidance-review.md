---
kind: command
role: opencode-command
description: Perform a focused scoped review of guidance in the repository
---

You are auditing and correcting a Django codebase against one specific repository guidance document.

Read this guidance document first and treat its central idea as the audit subject.

GUIDANCE_DOC: `$1`

Your job:

1. Read the guidance doc carefully and extract:
   - the subject of the document
   - the concrete rules, patterns, constraints, and anti-patterns
   - any required architecture, naming, layout, testing, or verification expectations

2. Do a deep codebase audit for that subject.
   - Search broadly for all related implementations, usages, examples, and near-misses
   - Include models, views, serializers, URLs, services, tests, middleware, management commands, admin, tasks, and shared utilities when relevant
   - Do not stop at the first example; find all meaningful occurrences

3. Build a compliance report.
   - List files that already follow the guidance
   - List files that partially follow it
   - List files that violate it
   - For each violation, explain exactly which rule is not being followed and why it matters

4. Update the code to comply with the guidance.
   - Make the smallest correct changes
   - Match existing repository patterns
   - Reuse existing shared helpers, base classes, and structures
   - Do not add speculative abstractions
   - Do not add backward-compatibility code unless clearly needed
   - Do not touch unrelated code

5. Add or update tests where the guidance implies behavior, scoping, permissions, serializer shape, routing, lifecycle rules, or other enforceable behavior.

6. Run relevant verification.
   - Run `ruff check` on modified Python files
   - Run targeted Django/pytest tests for changed areas
   - Run any other minimal relevant verification for the subject

7. Return a final report with these sections:
   - Subject
   - Guidance rules extracted
   - Files audited
   - Findings before changes
   - Changes made
   - Tests and verification run
   - Remaining gaps or follow-ups

Important requirements:
- Follow repository Django conventions
- Prefer direct, explicit code over defensive or generic code
- Keep views thin, serializers explicit, URLs predictable, tests readable
- If the repo already has a shared pattern for this subject, use it
- If no changes are needed in a file, say so only after checking it
- Be exhaustive, not sample-based