---
description: Contribute reusable guidance from this project to Agents through a focused pull request.
input: [context]
---

Find guidance in the current project that is genuinely reusable across repositories, then propose it to `https://github.com/GriffinBoris/Agents` in a focused pull request.

Optional context: `${input:context}`

Use this workflow only for a contribution to the shared package. Do not use it to update this project's installed guidance; use `task ai:install` with a pinned `AGENTS_PACKAGE` release for that.

## Decide whether a rule belongs upstream

- Inspect the requested scope, current diff, local guidance, relevant code, and tests.
- Treat repository architecture, product terms, local commands, customer details, secrets, migration constraints, and one-off workarounds as project-owned by default.
- Propose a rule only when it is useful in more than one repository, can be stated without private details, and fits the shared baseline, a language/framework skill, an example, or a review workflow.
- If no candidate meets that standard, make no branch or PR. State what should remain local and why.

## Make the smallest package change

- Read the relevant current package source in Agents before editing: `.apm/instructions/`, the matching `.apm/skills/` folder, and its `references/` when applicable.
- Work in a clean clone or worktree of the Agents repository. Do not mutate the current consumer project.
- Edit authored APM sources only. Do not change generated harness output.
- Generalize identifiers and examples. Prefer refining an existing skill or example instead of adding a duplicate.

## Verify and publish

Run from the Agents checkout:

```bash
apm compile --validate --local-only
apm audit
apm pack --archive --output dist
```

Review the complete diff for duplicate rules, project-specific material, secrets, and generated files. Then create a focused branch, commit the verified change, push it, and open a pull request against Agents' default branch.

The PR must state the reusable pattern, evidence for it, files changed, validation run, and what deliberately remains project-specific. If authentication, repository access, or a material classification decision is missing, preserve the proposed diff and ask for the minimum needed input.
