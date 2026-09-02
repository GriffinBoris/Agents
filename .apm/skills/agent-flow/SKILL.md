---
name: agent-flow
description: Run or resume a YAML Agent Flow workflow from a persistent Codex Desktop parent task using native Codex subagents as disposable workers. Use for staged research, planning, implementation, review, testing, and approval workflows; do not use for ordinary single-agent tasks.
---

# Agent Flow

## Scope

Keep the current Codex Desktop task as the persistent workflow parent. Execute `agent` and `parallel` steps with native Codex subagents so their activity is visible in Desktop and their results return to this parent.

Do not invoke `codex exec`, Claude Code, or another provider CLI. The `agent-flow` command only validates workflow definitions, records durable state, verifies artifacts, and runs declared shell steps.

If the user explicitly asks for a new or dedicated Desktop task, use the host's task-creation capability and instruct that task to invoke `$agent-flow`. Otherwise, run the workflow in the current task. Never create a separate task merely because the workflow has multiple steps.

## Workflow

1. Resolve the workflow file, request file, and target repository. Use `agent-flow` when it is installed; inside the Agent Flow source checkout, use `uv run agent-flow`. If neither is available, report the missing installation rather than substituting provider CLI calls.
2. For a new run, execute:

   ```text
   agent-flow start <workflow> --request <request> --repo <repository>
   ```

   When the user supplies a GitHub issue URL or number instead of a request file, execute:

   ```text
   agent-flow start <workflow> --issue <issue-url-or-number> --repo <repository>
   ```

   This uses the authenticated `gh` CLI read-only and snapshots the issue as the run's `request.md`.

   For an existing run, execute `agent-flow status <run-id> --repo <repository>`.
3. Treat the returned JSON as authoritative for the current step, model, effort, input paths, output path, delegation policy, and approval state.
4. Continue through ready steps until the run completes, fails, or reaches an approval gate. Do not skip, reorder, or silently substitute steps.

### Agent step

1. Run `agent-flow begin <run-id> <step-id> --repo <repository>` before spawning the worker.
2. Spawn one native subagent for the step. Pass the configured model and reasoning effort without substitution. Give it:
   - the rendered step prompt;
   - the exact resolved input paths;
   - the requested read or write mode;
   - the exact output path and requested report structure;
   - an instruction to return its complete artifact to the parent rather than writing the workflow artifact itself.
3. Read-mode workers must not modify repository files. Run write-mode workers sequentially in the parent's checkout.
4. After spawning, record the returned worker or thread identifier with:

   ```text
   agent-flow attach <run-id> <step-id> <worker-id> --repo <repository>
   ```

5. Coordinate through the parent. Send bounded follow-up instructions when the worker needs correction or missing context, wait for it to finish, and do not duplicate its assigned work in the parent.
6. Write the worker's final response to the exact output path from `status`.
7. Run `agent-flow complete <run-id> <step-id> --repo <repository>`. Completion verifies the artifact exists before advancing.
8. After the artifact is durable and no follow-up is needed, close the completed worker thread when the host supports closing. Otherwise leave it in the completed list; never delete useful output before it is captured.

When `delegation.strategy` is `native`, the step worker may itself spawn at most `max_agents` bounded subagents. Give it the configured delegated model, effort, and delegation instructions. It must wait for those children and return one synthesized artifact to the parent.

### Questions and decisions

Workers may send questions or escalations to the persistent parent while a step is running. When a question could materially affect behavior, scope, architecture, compatibility, permissions, published state, or destructive work:

1. Keep the current step running; do not invent an answer or mark it complete.
2. Present one concise question to the user with the relevant evidence, options, and impact.
3. Forward the user's answer to the same worker and let it continue. If that worker has already exited, retry the current step with the answer included and record the new worker ID.
4. Persist established decisions in the step artifact so later workers receive them.

Answer small, evidence-backed implementation questions within the parent only when the issue, repository guidance, or a prior explicit user decision determines the answer unambiguously.

### Parallel step

1. Run `agent-flow begin <run-id> <parallel-step-id> --repo <repository>` once.
2. Spawn one native subagent for each child concurrently. Parallel children are read-only and must have disjoint assignments.
3. Attach each worker to its child step id, not the enclosing parallel step id.
4. Wait for every child. Persist each final response to that child's declared output path.
5. Run `agent-flow complete <run-id> <parallel-step-id> --repo <repository>`. The controller verifies every child artifact exists before advancing.
6. Close completed child threads only after all required artifacts are durable.

### Shell step

Run the declared command through the controller:

```text
agent-flow shell <run-id> <step-id> --repo <repository>
```

The controller executes the stored argument vector without shell interpolation, records stdout and stderr, and advances only on success.

### Approval step

Present the approval message, relevant artifacts, and a concise account of what will happen next. Stop and wait for explicit user approval. Do not infer approval from the original request or from silence.

After approval, execute:

```text
agent-flow approve <run-id> --repo <repository>
```

Then continue from the returned step. If the user rejects the result or requests changes, do not approve; use the parent conversation to determine the bounded correction before changing workflow state.

An approval gate may serve as a human-controlled correction loop. Keep it waiting while bounded correction workers update the repository or artifacts, rerun the relevant validation, and present the gate again. There is no automatic approval and no generic unattended loop.

### Failure and retry

When an agent step cannot complete, record the failure:

```text
agent-flow fail <run-id> <step-id> --message <concise-error> --repo <repository>
```

Keep the parent task alive, report the failed step and available evidence, and retry only when the failure is safe to retry or the user supplies the needed direction. `begin` retries the same failed step and increments its attempt count; completed steps do not rerun.

## Coordination invariants

- The Desktop parent owns requirements, user decisions, approvals, and final synthesis.
- Workers own bounded execution. Their full scratch context stays out of the parent; return concise findings and the complete requested artifact.
- Route cross-worker communication through the parent. Share only the information another worker needs.
- Persist important results in the run directory before closing workers.
- Do not expose a worker's existence as proof that its output was accepted; a durable artifact and `complete` are the acceptance boundary.
- Do not substitute unavailable models, broaden permissions, create new tasks, push changes, or open pull requests unless the user separately authorizes those actions. Invoking a workflow that clearly declares a PR-publication step is authorization for that step only after its preceding approval gate is explicitly approved.

## Completion

When the run reaches `completed`, summarize the workflow outcome, link or name the durable artifacts, report validation commands and failures, and leave the persistent parent task available for follow-up.
