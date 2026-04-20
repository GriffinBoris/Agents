---
kind: command
role: opencode-command
description: Run the full task-review workflow through subagents by chaining the context, findings, and fix commands via artifact paths
---

Run the full `task-review` workflow through subagents.

Scope comes from `$ARGUMENTS`.
If no explicit scope is provided, use the committed current branch diff against `origin/main`.

This command must use two separate subagent phases.

Phase 1: review subagent
- launch one subagent for the review phase
- in that subagent, run `/task-review-context $ARGUMENTS`
- capture the returned context artifact path
- pass that exact context artifact path into `/task-review-findings <context-artifact-path>`
- capture the returned findings artifact path
- return the findings artifact path back to the parent session

Phase 2: fix subagent
- launch a second subagent for the fix phase
- pass the exact findings artifact path from phase 1 into `/task-review-fix <findings-artifact-path>`
- let that subagent load the sibling context artifact, build the plan, implement the fixes, verify the work, and update the fix artifact

Requirements:
- do not recompute the artifact path heuristically between phases when the prior command already returned it
- pass the first command output path into the second command
- pass the second command output path into the fix command
- keep the scope stable across both subagents
- use the docs artifacts as the handoff boundary between subagents

Final response requirements:
- return the findings artifact path
- return the fix artifact path
- briefly summarize whether the fix phase completed or stopped on a blocker
