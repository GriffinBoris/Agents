---
name: project-architecture
description: Apply this repository's detailed architecture, feature-placement, domain-boundary, integration, migration, and conditional workflow guidance. Use whenever work depends on repository-specific structure or behavior beyond shared guidance and any optional always-on project baseline.
---

# Project Architecture

## Scope

- Keep detailed or conditional repository guidance here and in directly linked references.
- Follow the always-on `project-baseline` instruction for essential commands, source roots, critical invariants, and local overrides when that optional instruction exists.
- Prefer the closest existing implementation when this skill does not define a project-specific choice.

## Workflow

1. Identify the repository-specific concern before loading detailed guidance.
2. Read only the references that own that concern.
3. Inspect the closest comparable implementation and preserve established boundaries.
4. Apply the repository-specific guidance together with the relevant shared language or framework skill.
5. Run the exact verification commands defined by the optional project baseline, an applicable reference, or the repository's tooling.

## Repository Map

<!-- Document feature placement, module ownership, domain boundaries, and important dependency direction. Remove this comment after editing. -->

## Reference Selection

<!-- Link each detailed reference directly and state the exact concern that requires reading it. Keep references one level below this skill. Remove this comment after editing. -->

## Local Conventions

<!-- Document conditional workflows, integration behavior, migration constraints, and feature-specific conventions. Keep rules needed on nearly every task in the project baseline instead. Remove this comment after editing. -->

## Completion Checklist

- When a project baseline exists, it and this skill do not duplicate the same rule.
- Every loaded reference was relevant to the task.
- The implementation follows the repository's actual structure and closest local patterns.
- Verification used the repository's required commands.
