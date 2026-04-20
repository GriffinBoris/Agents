---
kind: command
role: opencode-command
description: Load the scoped task-review findings, plan the fixes, and implement them step by step
---

Load the scoped repo context plus the dumped `task-review` findings, then plan and implement the fixes.

Scope comes from `$ARGUMENTS`.
If no explicit scope is provided, use the `current-branch-diff` scope.

Input mode:
- `$ARGUMENTS` may be either:
  - an explicit scope, or
  - a path to `docs/task-review/<scope-slug>/task-review-findings.md`
- if a findings artifact path is provided, use that file as the source of truth and derive the sibling context artifact path from the same folder

This is the third command in the three-command workflow.
Use it only after `task-review-context` and `task-review-findings` have already created their artifacts.

Artifact rules:
- use the same scope label and slug rules as `task-review-context`
- ensure `docs/task-review/<scope-slug>/task-review-context.md` exists
- ensure `docs/task-review/<scope-slug>/task-review-findings.md` exists
- read `docs/task-review/<scope-slug>/task-review-context.md`
- read `docs/task-review/<scope-slug>/task-review-findings.md`
- re-read only the current diff or the scoped files that matter for the open issues
- create or update `docs/task-review/<scope-slug>/task-review-fix.md`

Do this in order:
1. Refresh only the context that still matters for implementation.
2. Load the issues, context, guidance, and examples from the dumped artifacts.
3. Turn the issues into a small-step plan.
4. Execute the plan one focused task at a time.
5. Verify each completed task with the smallest relevant check.
6. Update the fix artifact with the plan, completed work, verification run, and remaining follow-ups.

`task-review-fix.md` must include, when relevant:
- loaded inputs:
  - context artifact path
  - findings artifact path
- refreshed implementation context
- issue ids being addressed
- prerequisite context refresh
- must-fix now
- should-fix soon
- follow-up refactors
- guidance and example updates
- execution log
- verification run
- remaining follow-ups

For each planned task include:
- sequence number
- issue ids covered
- exact files to touch
- desired change in plain language
- verification command or check
- done criteria

Execution rules:
- use the plan as the source of truth
- keep one task in progress at a time
- if the plan turns out to be wrong, update the plan instead of freelancing invisible scope drift
- when implementation needs a user decision, ask one short question and stop at that boundary

This command should both write the plan and carry the work through implementation whenever feasible.

You are in build mode for this command.
Make code changes, run the relevant verification, and record the results in the fix artifact.

In the final response, return the exact written fix artifact path and summarize what was fixed.
