---
name: migration-baseline
description: Port repository-owned or locally modified guidance from a legacy agents/ tree or AGENTS.md into the consumer's optional always-on project baseline and lazy project-architecture skill without duplicating shared package guidance. Use only when migrating an older repository's guidance layout.
---

# Legacy Guidance Port

## Scope

Port only guidance that belongs to, was added by, or was changed by the older repository. Current shared baseline, language, framework, testing, review, and example guidance comes from installing this package and must not be copied into local project guidance.

Use `.apm/instructions/project-baseline.instructions.md` only when the legacy repository has concise rules that must affect nearly every task or prevent unsafe or invalid work. Do not create an empty baseline. Use `.apm/skills/project-architecture/` for detailed or conditional repository guidance. Do not put the full legacy document into the always-on baseline.

Use [legacy-codex-AGENTS.md](references/legacy-codex-AGENTS.md) only as a comparison source for recognizing former shared content. Search or read only the relevant sections. Its SHA-256 is `2f1ea4481b85236a287645d2bcb83c626559d0060d961f8ea1bb0c1382744b43`.

## Workflow

1. Inventory legacy authored guidance under `agents/`, repository-specific instruction files, and any preserved aggregate `AGENTS.md`. Prefer authored sources; use generated aggregates only for content not represented by an authored source.
2. Identify known shared content using repository provenance when available and the historical snapshot when needed. Do not assume an old generated document is entirely shared or entirely local.
3. Classify every legacy section, rule, and example as a shared duplicate, an always-needed repository rule, conditional repository guidance, a local override or extension of shared guidance, or unresolved content.
4. Port repository-owned guidance and local deltas into the destinations below. Preserve the intent and relevant detail; do not weaken a rule merely to shorten it.
5. Produce a complete parity map and verify that every legacy item has either a current shared owner or a local destination.

## Destination Map

| Legacy content | Destination |
| --- | --- |
| Exact commands used for most tasks, primary source roots, universal safety or ownership invariants, required base types, or active local overrides that must not be missed | `.apm/instructions/project-baseline.instructions.md` |
| Detailed feature placement, domain architecture, conditional commands or workflows, integrations, product behavior, or migration notes | `.apm/skills/project-architecture/SKILL.md` or a directly linked file under its `references/` directory |
| Repository-specific examples | `.apm/skills/project-architecture/references/examples/` and a direct link from the skill |
| Local change to an otherwise shared rule | A concise override in `project-baseline` when it must affect most work; otherwise the local skill near the affected project rule, with the shared owner identified |
| Possibly reusable but not yet accepted shared guidance | Preserve locally and flag it as a candidate for promotion to the shared package |
| Unresolved ownership | Preserve locally in a clearly labeled reference and report it for review |

Do not copy legacy global, Python, Django, Vue, framework-testing, review, or shared example content when the installed package already owns it.

## Parity Map

For every legacy source section, report:

- legacy source and heading
- classification
- current shared owner or new local destination
- whether wording was preserved, intentionally adapted, or requires review

Do not declare the port complete while any legacy guidance is unmapped.

## Boundaries

- Port guidance only. Do not install or update the shared package, modify application code, publish changes, or synchronize upstream guidance as part of this workflow.
- Do not edit `apm_modules/`, generated `AGENTS.md`, or harness-generated skill and command directories.
- Do not delete legacy guidance during the port. Report when it is safe to remove only after the local sources, compiled output, and parity map have been reviewed.
- When ownership is uncertain, preserve the content locally instead of discarding it.
- Keep `project-baseline` concise when it is needed; omit it when no migrated rule requires always-on local context. Preserve detailed supporting material in `project-architecture` references instead of expanding always-on context.

## Completion Checklist

- Every legacy guidance source was inventoried.
- Every section, rule, and example has a shared owner, local destination, or explicit unresolved entry.
- Critical repository-owned guidance and local shared-rule overrides are present in `project-baseline` when any require always-on context; otherwise that file is absent.
- Detailed or conditional repository guidance is present in `project-architecture` and its references.
- Shared package guidance was not duplicated into `project-architecture`.
- Legacy sources remain available for final comparison and removal is only recommended after verification.
