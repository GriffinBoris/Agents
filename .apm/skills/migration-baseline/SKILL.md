---
name: migration-baseline
description: Use only when auditing migration parity or deciding where a historical rule belongs. It preserves the pre-APM aggregate source snapshot.
---

# Migration Baseline

## Scope

- Use the immutable pre-APM aggregate to audit migration parity or decide where a historical rule belongs.
- Preserve historical guidance while keeping it out of ordinary task context.

### Boundaries

- Do not load the duplicate aggregate for ordinary coding, implementation, or review tasks.
- Do not restore stack- or project-specific guidance to the always-on baseline merely because it existed in the historical aggregate.

## Workflow

1. Verify the historical snapshot checksum before using it as the parity source.
2. Search or read only the relevant historical section.
3. Compare the historical rule with the current baseline, owning skill, references, and examples.
4. Identify the current owner or record an explicit migration gap.
5. Preserve the rule's purpose when relocating or rewriting it.

## Reference Selection

- Load [legacy-codex-AGENTS.md](references/legacy-codex-AGENTS.md) only for historical parity work.
- Load the current owning guidance skill and relevant examples before deciding that a rule is missing.

## Review Criteria

- The snapshot is the complete pre-APM Codex aggregate captured before the legacy source tree and custom builder were removed.
- It contains every legacy guidance section and its example inventory.
- Full example bodies remain in their owning APM skill's `references/examples/` directory, where they are individually lazy-loadable.
- The current always-on baseline contains cross-stack guidance and skill routing rather than the duplicate aggregate.

## Output

- Identify the historical rule and its location.
- Identify its current owner and location.
- Record whether it is preserved, intentionally superseded, project-specific, or missing.
- Propose the smallest relocation or wording change needed to preserve its purpose.

## Completion Checklist

- The snapshot SHA-256 is `2f1ea4481b85236a287645d2bcb83c626559d0060d961f8ea1bb0c1382744b43`.
- The historical and current sources were compared directly.
- No duplicate aggregate was loaded into ordinary task guidance.
- Any genuine migration gap has an explicit owner.
