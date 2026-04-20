---
kind: command
role: opencode-command
description: Create a new authored OpenCode command in the modular content tree
---

Create a new command file in the authored modular tree.

Use the existing command files in `agents/content/commands/` as formatting references.
Create the new file at `agents/content/commands/$1.md`.

If `$1` is missing, ask for the command name.
Use `$2` as the description if provided.
Use the remaining arguments as the command body. If the body is missing, ask for the exact prompt text.

When creating the command:
- reference the modular guidance tree under `agents/guidance/`, not legacy `agents/*.md` paths
- prefer named skills under `agents/content/skills/` when a workflow is reusable
- keep the reusable skill set small and centered on `architecture-audit`, `backend-homogeneity-audit`, `frontend-homogeneity-audit`, and `context-gatherer` unless there is a strong reason to expand it
- keep review commands aligned with the rule that all verifiable in-scope guidance deviations must be listed
- keep frontend guidance references aligned with route-based `src/views/` structure, not `src/features/`

If the work reveals a reusable command or skill convention, update the authored docs in `agents/content/` or `agents/guidance/` rather than generated output.

Return the new file path and a brief usage example.
