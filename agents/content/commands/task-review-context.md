---
kind: command
role: opencode-command
description: Gather scoped task-review context and dump matching guidance examples into a repeatable docs artifact
---

Gather the scoped context for a `task-review` and dump it to one repeatable docs artifact.

Scope comes from `$ARGUMENTS`.
If no explicit scope is provided, use the committed current branch diff against `origin/main`.

Input mode:
- `$ARGUMENTS` is a review scope, not an artifact path, for this command

Scope rules:
- explicit scope wins over git diff
- default diff scope means `git diff origin/main...HEAD`
- do not silently mix committed diff scope with dirty working tree changes
- if the user wants uncommitted changes included, they must say so explicitly

Artifact rules:
- derive a stable scope label
- derive a stable scope slug
- explicit scope slug: lowercase kebab-case version of the requested scope
- no explicit scope slug: `current-branch-diff`
- create or update `docs/task-review/<scope-slug>/task-review-context.md`

Use `context-gatherer` when the scope is broad, unfamiliar, or concept-based.

This command must gather:
- scoped repo context
- relevant guidance files
- example file names and frontmatter metadata
- the matching examples for the scoped area

Do not perform the final review in this command.
Do not produce the final issue list yet.

`task-review-context.md` must include:
- review goal
- scope source: `explicit` or `current-branch-diff`
- exact scope text
- included files, folders, workflows, concepts, or changed files
- excluded or lightly checked areas
- active stacks and concern buckets in scope
- structure inventory with concrete file paths
- key components and responsibilities
- important flows through the scope
- closest relevant guidance files
- matching examples with repeatable metadata fields:
  - example file path
  - filename
  - title
  - description
  - tags
  - applies_to
- closest local reference implementations already in the repo
- open questions, assumptions, and blind spots

Use a repeatable format with short titled sections and explicit file paths.

When the scope is a diff, cover every changed file or changed area in the context artifact.
When the scope is concept-based, cover every concrete file or subsystem the concept touches.

Keep the artifact under `docs/task-review/` as a temporary working review document.

In the final response, return the exact written context artifact path.
