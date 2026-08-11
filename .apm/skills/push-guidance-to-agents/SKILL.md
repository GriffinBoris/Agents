---
name: push-guidance-to-agents
description: Contribute reusable guidance from a consumer repository to GriffinBoris/Agents through a focused change or pull request. Use only when the user explicitly asks to promote, contribute, push, or upstream guidance to the shared Agents repository; never trigger for ordinary local guidance edits, package installation, or upgrades.
---

# Push Guidance to Agents

## Scope

- Identify guidance in the current project that is genuinely reusable across repositories and propose it to `https://github.com/GriffinBoris/Agents`.
- Keep repository architecture, product terms, local commands, customer details, secrets, migration constraints, and one-off workarounds project-owned by default.
- Use this workflow only for contributions to the shared package. Update installed guidance through the package installation workflow instead.

## Workflow

1. Inspect the requested scope, current diff, local guidance, relevant code, and tests.
2. Propose a rule only when it is useful in more than one repository, can be stated without private details, and has a clear owner in the shared baseline, a language or framework skill, an example, or an audit workflow.
3. If no candidate meets that standard, make no branch or pull request. Explain what should remain local and why.
4. Read the relevant current source in Agents before editing: `.apm/instructions/`, the owning `.apm/skills/` folder, and any applicable references.
5. Work in a clean clone or worktree of Agents. Do not mutate the consumer repository while preparing the shared-package change.
6. Edit authored APM sources only. Generalize identifiers and examples, and refine an existing owner instead of adding a duplicate when possible.
7. Validate the package change, review the complete diff, and publish only when the user's request authorizes the required commit, push, and pull request.

## Verification

Run from the Agents checkout:

```bash
apm compile --validate --local-only
apm audit
git diff --check
```

Do not use `apm pack` as the source-package release workflow. The repository's README defines the current release and consumer-install process.

## Boundaries

- Never include secrets, private details, generated harness files, or consumer-specific architecture in the shared package.
- Do not publish a speculative rule without evidence from a real implementation or repeated need.
- Do not commit, push, or open a pull request when the user requested only a proposal or review.
- If authentication, repository access, or a material classification decision is missing, preserve the proposed local diff and ask for the minimum required input.

## Completion Checklist

- The contribution is reusable and has one clear shared owner.
- Project-specific material remains in the consumer repository.
- The package diff is focused, generalized, and free of generated files.
- Package validation and diff checks passed or their blockers are explicit.
- The final report states the reusable pattern, evidence, files changed, verification, and deliberately local material.
