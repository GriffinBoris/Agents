---
name: migration-baseline
description: Use only when auditing migration parity or deciding where a historical rule belongs. It preserves the pre-APM aggregate source snapshot.
---

# Migration Baseline

`references/legacy-codex-AGENTS.md` is the complete pre-APM Codex aggregate captured before the legacy source tree and custom builder were removed.

The reference has SHA-256 `2f1ea4481b85236a287645d2bcb83c626559d0060d961f8ea1bb0c1382744b43`. It contains every legacy guidance section and its example inventory. Full example bodies remain in their owning APM skill's `references/examples/` directory, where they are individually lazy-loadable.

During migration, `.apm/instructions/engineering-baseline.instructions.md` retains the aggregate as the always-on instruction, with legacy source links rewritten to installed skill and reference locations. Use this skill only to identify an unmapped historical rule or decide where a rule should live after the later context-reduction phase. Do not load this duplicate aggregate reference for ordinary coding tasks.
