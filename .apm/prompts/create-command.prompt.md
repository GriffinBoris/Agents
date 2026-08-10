---
description: Create a new portable APM prompt in this package.
input: [command_name, description]
---

Create a new command file in the authored modular tree.

Use the existing prompt files in `.apm/prompts/` as formatting references.
Create the new file at `.apm/prompts/${input:command_name}.prompt.md`.

If `${input:command_name}` is missing, ask for the command name.
Use `${input:description}` as the description if provided.
Use the remaining arguments as the command body. If the body is missing, ask for the exact prompt text.

When creating the command:
- reference the native `.apm/` guidance tree, not generated target output
- prefer named skills under `.apm/skills/` when a workflow should be auto-discovered
- keep the reusable skill set small and centered on `architecture-audit`, `backend-homogeneity-audit`, `frontend-homogeneity-audit`, and `context-gatherer` unless there is a strong reason to expand it
- keep review commands aligned with the rule that all verifiable in-scope guidance deviations must be listed
- keep frontend guidance aligned with the consuming repository's established route root, as defined by `project-architecture` and nearby code; do not impose `src/views/` or `src/features/` universally

If the work reveals a reusable prompt or skill convention, update the authored `.apm/` source rather than generated output.

Return the new file path and a brief usage example.
