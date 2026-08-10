---
description: Audit and correct code against one specific guidance document.
input: [guidance_doc]
---

Audit and correct the codebase against one specific repository guidance document.

Read this guidance document first and treat its central idea as the audit subject.
Load `review-workflows` and use its shared scope, evidence, findings, and reporting rules throughout the audit.

GUIDANCE_DOC: `${input:guidance_doc}`

Your job:

1. Read the guidance doc carefully and extract:
   - the subject of the document
   - the concrete rules, patterns, constraints, and anti-patterns
   - any required architecture, naming, layout, testing, or verification expectations

2. Do a deep codebase audit for that subject.
   - Search broadly for all related implementations, usages, examples, and near-misses
   - Include every relevant surface for the active stack, such as models, endpoints, services, tasks, stores, routes, components, tests, commands, middleware, and shared utilities

3. Build a compliance report.
   - List files that already follow the guidance
   - List files that partially follow it
   - List files that violate it
   - For each violation, explain exactly which rule is not being followed and why it matters

4. Update the code to comply with the guidance.
   - Apply the shared review's simplest appropriate fix direction without changing unrelated code

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

If no changes are needed in an audited file, record that result only after checking it. Preserve the selected guidance's purpose and architectural boundaries while applying the repository's established pattern.
