---
description: Audit and correct code against one specific guidance document.
input: [guidance_doc]
---

Audit and correct the codebase against one specific repository guidance document.

Read this guidance document first and treat its central idea as the audit subject.

GUIDANCE_DOC: `${input:guidance_doc}`

Your job:

1. Read the guidance doc carefully and extract:
   - the subject of the document
   - the concrete rules, patterns, constraints, and anti-patterns
   - any required architecture, naming, layout, testing, or verification expectations

2. Do a deep codebase audit for that subject.
   - Search broadly for all related implementations, usages, examples, and near-misses
   - Include every relevant surface for the active stack, such as models, endpoints, services, tasks, stores, routes, components, tests, commands, middleware, and shared utilities
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

5. Add or update tests where the guidance implies behavior, scoping, permissions, data-contract shape, routing, lifecycle rules, or other enforceable behavior.

6. Run relevant verification.
   - Use the repository's commands for the active stack and changed files
   - Run the relevant linter or static checks
   - Run targeted tests for changed behavior
   - Run any additional minimal verification required by the guidance subject

7. Return a final report with these sections:
   - Subject
   - Guidance rules extracted
   - Files audited
   - Findings before changes
   - Changes made
   - Tests and verification run
   - Remaining gaps or follow-ups

Important requirements:
- Follow the relevant baseline, language, framework, and repository conventions
- Prefer direct, explicit code over defensive or generic code
- Preserve the architectural boundaries taught by the selected guidance
- If the repo already has a shared pattern for this subject, use it
- If no changes are needed in a file, say so only after checking it
- Be exhaustive, not sample-based
