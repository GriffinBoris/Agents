# Agent Flow

Agent Flow runs repeatable Codex CLI and Claude Code workflows without carrying an entire conversation from one stage to the next. Every agent stage starts with fresh context and receives only the repository plus explicitly listed input artifacts.

## Install

Install the CLI from a checkout:

```bash
uv tool install .
agent-flow --help
```

For development:

```bash
uv sync --extra dev
uv run agent-flow --help
```

Codex stages use the authentication saved by `codex login`. Claude stages use the authentication available to `claude`. Agent Flow does not read, copy, or persist provider credentials.

## Run a workflow

Create a request file, then start a run against the target repository:

```bash
agent-flow run workflows/deep-feature.yml \
  --request request.md \
  --repo /path/to/repository
```

The command prints the run ID, run directory, and current status as JSON. A run stores its durable state in the target repository:

```text
.agent-flow/runs/<run-id>/
├── artifacts/
├── events.jsonl
├── logs/
├── request.md
├── state.json
└── workflow.json
```

`workflow.json` is a resolved snapshot. It includes prompt-file content and JSON schemas so edits to the source workflow do not change a run that is already in progress.

## Approve and resume

An approval step saves `waiting_for_approval` state and exits successfully. Review the named artifacts, then continue the run:

```bash
agent-flow approve <run-id> --repo /path/to/repository
agent-flow resume <run-id> --repo /path/to/repository
```

Inspect a run without changing it:

```bash
agent-flow status <run-id> --repo /path/to/repository
```

When an agent or shell step fails, Agent Flow records the error and leaves the step cursor in place. `resume` reruns that step. Completed steps do not run again.

## Workflow format

A workflow defines named model profiles and an ordered list of steps:

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
    command: ["python3", "-m", "pytest", "-q"]
```

All file paths in a workflow are relative. Prompt and schema files are relative to the workflow file. Inputs resolve first against the run directory and then against the target repository. Outputs always stay inside the run directory.

### Model profiles

Each agent step selects a named model profile through `model`. When the step omits it, the runner uses `defaults.model`.

```yaml
models:
  codex-review:
    provider: codex
    model: gpt-5.6-sol
    effort: high

  claude-review:
    provider: claude
    model: opus
    effort: high
```

Agent Flow passes model names directly to the provider CLI and does not silently substitute an unavailable model. The resolved profile and provider metadata are recorded in run state.

### Agent steps

Agent steps support:

| Field | Required | Purpose |
| --- | --- | --- |
| `id` | Yes | Unique step identifier. |
| `type` | Yes | Must be `agent`. |
| `model` | When no default exists | Named model profile. |
| `mode` | No | `read` by default; `write` permits repository changes. |
| `prompt` or `prompt_file` | Yes | Inline task instructions or a relative prompt file. |
| `inputs` | No | Run artifacts or repository files available to the stage. |
| `output` | No | Run-relative artifact path. A default path is used when omitted. |
| `schema` or `schema_file` | No | JSON Schema for the final stage result. |
| `allowed_tools` | No | Claude Code tool allowlist. |
| `delegation` | No | Native provider subagent policy. Delegation is off by default. |

Codex read stages use its read-only sandbox; write stages use `workspace-write`. Claude read stages use plan permission mode; write stages use `acceptEdits`. A non-interactive provider run cannot answer a new approval prompt, so configure each stage with the permissions and tool allowlist it needs.

When a stage declares a schema, Agent Flow parses and validates the provider result locally before writing the artifact or exposing it to a later stage.

### Native subagents

Native delegation keeps temporary exploratory work inside one provider stage:

```yaml
delegation:
  strategy: native
  max_agents: 3
  default_model: fast
  instructions: Give each subagent a distinct package and request exact file references.
```

The delegated model must use the same provider as the parent stage. Agent Flow configures Codex subagent defaults and concurrency. For Claude Code, it supplies a bounded `workflow-worker` custom subagent and directs the parent to use it. `max_agents` is enforced by Codex configuration and by the rendered task instruction; Claude Code currently receives the limit as an instruction.

Use native subagents for disposable exploration, log analysis, and research. Use a parallel step when each result must be a durable, independently retryable workflow artifact.

### Parallel steps

A parallel step launches its child agent processes concurrently:

```yaml
- id: reviews
  type: parallel
  steps:
    - id: correctness
      type: agent
      model: codex-review
      mode: read
      prompt_file: prompts/review-correctness.md
      inputs: [plan.md]
      output: correctness-review.json
      schema_file: schemas/review.json

    - id: simplicity
      type: agent
      model: claude-review
      mode: read
      prompt_file: prompts/review-simplicity.md
      inputs: [plan.md]
      output: simplicity-review.json
      schema_file: schemas/review.json
```

The first release permits only read-mode agent children. This prevents concurrent agents from editing the same checkout. If one child fails, the group fails after the other children finish; resuming reruns the group.

### Shell steps

Shell commands use an argument list and run directly without a shell:

```yaml
- id: tests
  type: shell
  command: ["uv", "run", "pytest", "-q"]
  output: test-output.txt
```

This avoids shell interpolation. Use a checked-in script when a command needs pipes, redirection, or complex shell control flow.

## Current limits

- Workflows are ordered lists; there is no generic `if`, loop, or arbitrary DAG syntax yet.
- Parallel children are read-only agent steps.
- Resume reruns every child in a failed parallel group.
- Provider processes are local child processes and do not become separate Codex Desktop sidebar tasks.
- Cancellation, timeouts, worktree management, and live event streaming are not implemented.

These constraints keep the execution and recovery model small enough to audit. Add control-flow features only after repeated workflows demonstrate a concrete need.
