---
name: migration-baseline
description: Port repository-owned or locally modified guidance from a legacy agents/ tree or AGENTS.md into the consumer's local APM project-architecture skill without duplicating shared package guidance. Use only when migrating an older repository's guidance layout.
---

# Legacy Guidance Port

## Scope

Port only guidance that belongs to, was added by, or was changed by the older repository. Current shared baseline, language, framework, review, and example guidance comes from installing this package and must not be copied into local project guidance.

Use [legacy-codex-AGENTS.md](references/legacy-codex-AGENTS.md) only as a comparison source for recognizing former shared content. Search or read only the relevant sections. Its SHA-256 is `2f1ea4481b85236a287645d2bcb83c626559d0060d961f8ea1bb0c1382744b43`.

## Workflow

1. Inventory legacy authored guidance under `agents/`, repository-specific instruction files, and any preserved aggregate `AGENTS.md`. Prefer authored sources; use generated aggregates only for content not represented by an authored source.
2. Identify known shared content using repository provenance when available and the historical snapshot when needed. Do not assume an old generated document is entirely shared or entirely local.
3. Classify every legacy section, rule, and example as a shared duplicate, repository-owned guidance, a local override or extension of shared guidance, or unresolved content.
4. Port repository-owned guidance and local deltas into the destinations below. Preserve the intent and relevant detail; do not weaken a rule merely to shorten it.
5. Produce a complete parity map and verify that every legacy item has either a current shared owner or a local destination.

## Destination Map

| Legacy content | Destination |
| --- | --- |
| Repository architecture, paths, commands, tooling, product behavior, or active exceptions | `.apm/skills/project-architecture/SKILL.md` |
| Long repository-specific rules or migration notes | A directly linked file under `.apm/skills/project-architecture/references/` |
| Repository-specific examples | `.apm/skills/project-architecture/references/examples/` and a direct link from the skill |
| Local change to an otherwise shared rule | The local skill near the affected project rule, with the shared rule or owner identified |
| Possibly reusable but not yet accepted shared guidance | Preserve locally and flag it as a candidate for promotion to the shared package |
| Unresolved ownership | Preserve locally in a clearly labeled reference and report it for review |

Do not copy legacy global, Python, Django, Vue, review, or shared example content when the installed package already owns it.

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

## Completion Checklist

- Every legacy guidance source was inventoried.
- Every section, rule, and example has a shared owner, local destination, or explicit unresolved entry.
- Repository-owned guidance and local shared-rule deltas are present in local authored APM sources.
- Shared package guidance was not duplicated into `project-architecture`.
- Legacy sources remain available for final comparison and removal is only recommended after verification.
