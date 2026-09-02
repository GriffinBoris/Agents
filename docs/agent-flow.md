# Agent Flow

Agent Flow runs repeatable engineering workflows from a persistent Codex Desktop task. The Desktop task is the workflow parent: it retains requirements and decisions, spawns native Codex subagents, coordinates follow-ups, handles approvals, and presents the final result. Subagents use fresh contexts and become disposable after their accepted outputs are stored.

The Python package is deliberately not an agent launcher. It validates YAML, snapshots the workflow, records state and worker IDs, verifies artifacts, and executes declared shell commands.

## Architecture

```text
Codex Desktop parent task
├── Agent Flow skill
├── native research worker ──→ research.md
├── native planning worker ──→ plan.md
├── native implementation worker ──→ repository changes
├── parallel native reviewers ──→ review artifacts
└── agent-flow controller ──→ state, validation, shell steps
```

The parent task stays visible in Desktop. Native worker threads are inspectable while they run and return their results to the parent. After the parent persists and validates a result, the worker can be closed or left in Desktop's completed list.

## Install

Install the controller from a checkout:

```bash
uv tool install .
agent-flow --help
```

For development in this repository:

```bash
uv sync --extra dev
uv run agent-flow --help
```

The `agent-flow` skill is authored at `.apm/skills/agent-flow/`. Compile this package for Codex or install it through APM so Desktop can discover the skill.

## Run from Desktop

Invoke the skill in a Codex Desktop task:

```text
$agent-flow Run examples/agent-flow/deep-feature.yml with examples/agent-flow/request.md against this repository.
```

For the GitHub-issue-to-PR example, the issue itself becomes the snapshotted request:

```text
$agent-flow Run examples/agent-flow/github-issue-to-pr.yml for https://github.com/OWNER/REPO/issues/123 against /path/to/REPO.
```

The parent starts that workflow with:

```bash
agent-flow start examples/agent-flow/github-issue-to-pr.yml \
  --issue https://github.com/OWNER/REPO/issues/123 \
  --repo /path/to/REPO
```

`--issue` calls the authenticated `gh` CLI read-only and stores the issue metadata and body as the run's `request.md`. Use `--request` instead for a local specification. The two options are mutually exclusive.

The current task is the parent by default. If you explicitly ask for a dedicated task, the invoking task may create one and instruct it to run the skill. Agent steps do not create unrelated sidebar tasks; they use native subagents beneath the parent.

The skill begins a run with:

```bash
agent-flow start workflows/deep-feature.yml \
  --request request.md \
  --repo /path/to/repository
```

The command returns the current step as JSON, including resolved input and output paths, the selected model and effort, the prompt, and the delegation policy. The Desktop parent uses that descriptor to spawn a native worker.

## Controller lifecycle

The controller exposes small state transitions rather than a background daemon:

```text
agent-flow start <workflow> --request <file> --repo <repository>
agent-flow start <workflow> --issue <issue-url-or-number> --repo <repository>
agent-flow status <run-id> --repo <repository>
agent-flow begin <run-id> <step-id> --repo <repository>
agent-flow attach <run-id> <step-id> <worker-id> --repo <repository>
agent-flow complete <run-id> <step-id> --repo <repository>
agent-flow fail <run-id> <step-id> --message <error> --repo <repository>
agent-flow shell <run-id> <step-id> --repo <repository>
agent-flow approve <run-id> --repo <repository>
```

`begin` marks the current step as running. `attach` records the native worker returned by Desktop. The parent writes the worker's final response to the declared artifact path, then `complete` verifies it exists and advances. A failed step remains current and can be retried with `begin`; completed steps do not rerun.

An approval step saves `waiting_for_approval` state. The Desktop parent presents the message and relevant artifacts, then stops. Only explicit user approval permits `agent-flow approve`.

While a native worker is running, it can escalate a material ambiguity to the parent. The parent asks the user in the visible Desktop task, forwards the answer to that worker, and records the decision in the durable artifact. Approval gates can also act as human-controlled correction loops: requested changes are implemented and revalidated while the gate remains waiting, and the workflow advances only after explicit approval.

## Durable state

Each run stores its durable state in the target repository:

```text
.agent-flow/runs/<run-id>/
├── artifacts/
├── events.jsonl
├── logs/
├── request.md
├── state.json
└── workflow.json
```

`workflow.json` is a resolved snapshot containing prompt-file contents. Later edits to the source workflow do not alter an active run. `state.json` records attempts, worker IDs, failures, artifact paths, and the current step.

The Desktop conversation remains the human-visible coordination history. The run directory is the durable, machine-readable recovery boundary.

## Workflow format

A workflow defines Codex model profiles and an ordered list of steps:

```yaml
version: 1
name: focused-change

models:
  deep:
    provider: codex
    model: gpt-5.6-sol
    effort: high

  fast:
    provider: codex
    model: gpt-5.6-luna
    effort: medium

defaults:
  model: deep

steps:
  - id: research
    type: agent
    mode: read
    prompt_file: prompts/research.md
    inputs: [request.md]
    output: research.md
    delegation:
      strategy: native
      max_agents: 3
      default_model: fast
      instructions: Split documentation, code exploration, and dependency analysis.

  - id: approve-research
    type: approval
    message: Review research.md before planning.

  - id: tests
    type: shell
    command: ["uv", "run", "pytest", "-q"]
    output: test-output.txt
```

Prompt files are relative to the workflow file. Inputs resolve first against the run directory and then against the target repository. Outputs stay inside the run directory.

### Agent steps

Every agent step becomes one native Desktop subagent. The parent passes only the step prompt, explicit input paths, permissions, and output contract. The worker returns the complete artifact to the parent; the parent persists it and calls `complete`.

| Field | Required | Purpose |
| --- | --- | --- |
| `id` | Yes | Unique step identifier. |
| `type` | Yes | Must be `agent`. |
| `model` | When no default exists | Named Codex model profile. |
| `mode` | No | `read` by default; `write` permits repository changes. |
| `prompt` or `prompt_file` | Yes | Inline instructions or a workflow-relative prompt file. |
| `inputs` | No | Run artifacts or repository files supplied to the worker. |
| `output` | No | Run-relative artifact path; a default is used when omitted. |
| `delegation` | No | Whether the step worker may spawn bounded native children. |

The controller passes model names and effort values to the skill unchanged. The skill must not silently substitute an unavailable model.

### Nested native subagents

An agent step can permit its worker to delegate smaller tasks:

```yaml
delegation:
  strategy: native
  max_agents: 3
  default_model: fast
  instructions: Give each child a distinct package and request exact file references.
```

The step worker remains responsible for its children. It waits for them, synthesizes their results, and returns one artifact to the Desktop parent. Important information must reach the parent artifact before children are closed.

Use nested delegation for bounded exploration or analysis. Keep workflow-level stages in the main YAML when their outputs need independent validation, retry, or approval.

### Parallel steps

A parallel step asks the Desktop parent to spawn one native worker per child concurrently:

```yaml
- id: reviews
  type: parallel
  steps:
    - id: correctness
      type: agent
      model: deep
      mode: read
      prompt_file: prompts/review-correctness.md
      inputs: [plan.md]
      output: correctness-review.md

    - id: simplicity
      type: agent
      model: fast
      mode: read
      prompt_file: prompts/review-simplicity.md
      inputs: [plan.md]
      output: simplicity-review.md
```

Parallel children must be read-only. The parent waits for every worker, persists each output, and completes the group only after every artifact validates.

### Shell steps

Shell commands are stored as argument lists and executed directly without shell interpolation:

```yaml
- id: tests
  type: shell
  command: ["uv", "run", "pytest", "-q"]
  output: test-output.txt
```

Use a checked-in script when a command requires pipes, redirection, or complex shell behavior.

## Communication model

- The Desktop parent owns requirements, decisions, approvals, and final synthesis.
- Workers communicate findings and questions back to the parent through native subagent messaging.
- Cross-worker context is routed deliberately by the parent rather than shared automatically.
- Scratch context stays inside workers; accepted results become run artifacts.
- A worker is logically disposable only after its result is durable and accepted.

This keeps the parent coherent without reducing workers to disconnected subprocesses.

## Current limits

- The Desktop-native path currently supports Codex workers only. ACP-backed external providers can be added later, but they will not automatically become native Desktop child threads.
- The workflow is an ordered list; there is no generic unattended conditional, loop, or arbitrary DAG syntax. Repeatable correction passes can be declared as explicit steps, and approval gates support user-controlled correction loops.
- Parallel children are read-only agent steps.
- The parent task must remain available to coordinate native workers; the controller is not an unattended daemon.
- Closing completed worker threads depends on host capability. Completed threads may remain inspectable in Desktop.
- Cancellation, timeouts, and automatic worktree management are not implemented.

These constraints keep the execution model visible, recoverable, and aligned with Codex Desktop's native parent/subagent behavior.
