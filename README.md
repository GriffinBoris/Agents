# Agents

Shared engineering guidance for Codex, Claude Code, OpenCode, Copilot, and Gemini. Install a pinned release with [APM](https://github.com/microsoft/apm); use skills, workflows, and examples when a task needs them.

## Experimental Desktop-native agent workflows

This repository also contains `agent-flow`, a small file-backed controller for workflows run from a persistent Codex Desktop task. The Desktop task remains the parent and uses native Codex subagents as fresh, disposable workers. The controller provides:

- YAML workflows and named model/reasoning profiles
- Durable step state, artifacts, worker IDs, and retry history
- Read-only parallel agent groups
- Deterministic shell commands and explicit approval gates
- Durable Markdown artifacts before a worker result is accepted
- GitHub issue intake through `gh`, question routing through the visible parent, and approval-controlled correction loops

Install the controller, then invoke the bundled `agent-flow` skill from Codex Desktop:

```bash
uv tool install .
```

```text
$agent-flow Run examples/agent-flow/deep-feature.yml against this repository. Initial request: add the requested feature and validate it against repository guidance.
```

Inline request text is snapshotted inside the run as `request.md`; no separate request file is required. Local request files remain supported for longer specifications.

Open the live, read-only viewer for the most recent run:

```bash
agent-flow view --repo /path/to/repository
```

Pass a run ID to select a particular run. The viewer opens on `127.0.0.1`, refreshes from `.agent-flow/runs/` every two seconds, and shows workflow progress, parallel children, attached native workers, events, artifacts, and the resolved workflow definition.

Or run the issue-to-PR example without creating a request file:

```text
$agent-flow Run examples/agent-flow/github-issue-to-pr.yml for https://github.com/OWNER/REPO/issues/123 against /path/to/REPO.
```

The skill drives native Desktop subagents; the Python command does not launch Codex or Claude processes. Run state and artifacts live under `.agent-flow/runs/` in the target repository. See [Agent Flow](docs/agent-flow.md) for the workflow format, controller commands, live viewer, and current limitations.

## Use it in a project

Install or upgrade to APM **v0.28.0+** and verify the active binary before continuing:

```bash
curl -sSL https://aka.ms/apm-unix | sh
hash -r
apm --version
```

Before installing the shared package, download the repository-owned architecture template:

```bash
mkdir -p .apm/skills/project-architecture
curl -fsSL https://raw.githubusercontent.com/GriffinBoris/Agents/v0.1.0/templates/project-architecture.md -o .apm/skills/project-architecture/SKILL.md
```

Edit it with detailed architecture, feature placement, conditional workflows, integrations, migration notes, and project-specific examples. Its body and references load only when relevant.

Add a project baseline only when the repository has critical local facts that must be visible for nearly every task. Do not create or keep an empty baseline:

```bash
mkdir -p .apm/instructions
curl -fsSL https://raw.githubusercontent.com/GriffinBoris/Agents/v0.1.0/templates/project-baseline.txt -o .apm/instructions/project-baseline.instructions.md
```

Use it for exact commands, primary source roots, universal safety or ownership invariants, and local overrides that must not be missed. It is compiled into always-on harness guidance, so keep it concise. State each rule in one place; do not copy the same guidance into both local files.

These local authored sources keep repository-specific guidance under the consumer repository's control and prevent package upgrades from overwriting it.

The baseline template uses a `.txt` extension only to keep APM from treating the source-package template as shared guidance. Save it under the `.instructions.md` destination shown above.

### Install directly with APM

Append the generated-output ignore snippet once; do not replace the project's existing `.gitignore`. If the project already keeps hand-authored files in one of the listed generated paths, move that guidance into `.apm/` or omit the conflicting ignore line.

```bash
curl -fsSL https://raw.githubusercontent.com/GriffinBoris/Agents/v0.1.0/templates/gitignore.apm >> .gitignore
```

Install the pinned guidance package and compile the harness outputs:

```bash
apm install GriffinBoris/Agents#v0.1.0 --target claude,codex,opencode
apm compile --target claude,codex,opencode
```

`apm install` creates `apm.yml` when needed or adds the dependency to an existing manifest. Validate the local guidance and installed package after installation:

```bash
apm compile --validate --local-only
apm audit
```

Generated `AGENTS.md`, harness directories, and `apm_modules/` stay ignored. Commit the consumer's `apm.yml`, `apm.lock.yaml`, and `.apm/skills/project-architecture/` source. Commit `.apm/instructions/project-baseline.instructions.md` only when the repository needs that optional always-on guidance.

To upgrade, install another reviewed tag and compile again:

```bash
apm install GriffinBoris/Agents#v0.2.0 --target claude,codex,opencode
apm compile --target claude,codex,opencode
```

There is no separate pull or merge command. `apm install` resolves the chosen package version and `apm compile` rebuilds generated harness files.

For a private package, authenticate with a GitHub token that has repository read access before installing:

```bash
export GITHUB_APM_PAT="<token>"
apm install GriffinBoris/Agents#v0.1.0 --target claude,codex,opencode
apm compile --target claude,codex,opencode
```

### Use shared workflows

Reusable workflows install as skills so Codex, Claude Code, and OpenCode can discover them from their supported skill locations.

| Skill | Purpose |
| --- | --- |
| `full-review` | Review a branch diff, selected area, workflow, guidance package, or repository comprehensively. |
| `guidance-review` | Audit a codebase against one named guidance document and correct deviations when requested. |
| `review-git-diff` | Review the current branch diff against `origin/main`. |
| `push-guidance-to-agents` | Contribute verified reusable guidance to this shared package when explicitly requested. |

Ask for a workflow by name, for example:

```text
Use full-review to review the current branch changes.
Use guidance-review with .apm/skills/project-architecture/SKILL.md and correct the verified deviations.
```

Codex users can also invoke a skill explicitly with `$full-review` or select it through `/skills`. Skill bodies load only after invocation or a matching request; they are not added to the always-on `AGENTS.md` context.

### Optional Task wrapper

If the project uses [Task](https://taskfile.dev), download the ready-made wrapper from the same tagged release:

```bash
mkdir -p tasks
curl -fsSL https://raw.githubusercontent.com/GriffinBoris/Agents/v0.1.0/templates/tasks/ai.yml -o tasks/ai.yml
```

Add the Task namespace to the project's `Taskfile.yml`:

```yaml
includes:
  ai:
    taskfile: ./tasks/ai.yml
    dir: .
```

Then run `task ai:install` and `task ai:check`. The wrapper provides:

| Command | Purpose |
| --- | --- |
| `task ai:install` | Initialize APM if needed, install the pinned guidance package, and compile outputs. |
| `task ai:generate` | Rebuild generated harness files after a local guidance change. |
| `task ai:check` | Validate local guidance and detect installed-package drift. |
| `task ai:setup` | Alias for `install`. |

The template defaults to Codex, Claude Code, and OpenCode. Override its package or targets when needed:

```bash
AGENTS_PACKAGE=GriffinBoris/Agents#v0.2.0 task ai:install  # upgrade to a reviewed release
APM_TARGETS=claude,codex,opencode,copilot,gemini task ai:install
```

### Optional pre-commit hooks

If the project uses [pre-commit](https://pre-commit.com), `uv`, Ruff, isort, and the optional Task wrapper, add this local repository entry to `.pre-commit-config.yaml`. If the file already has a `repos:` key, add only the `repo: local` entry beneath it.

```yaml
repos:
  - repo: local
    hooks:
      - id: lint-code
        name: Ruff Lint
        entry: bash -c "uv run ruff check --fix"
        language: system
        types: [python]
        pass_filenames: false

      - id: format-code
        name: Ruff Format
        entry: bash -c "uv run ruff format"
        language: system
        types: [python]
        pass_filenames: false

      - id: sort-imports
        name: Sort Imports
        entry: bash -c "uv run isort ."
        language: system
        types: [python]
        pass_filenames: false

      - id: setup-all-agents
        name: Setup All Agents
        entry: bash -c "task ai:setup"
        language: system
        pass_filenames: false
```

Install the hooks and run them once:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

### Migrate an older repository

Keep the legacy `agents/` sources and any existing `AGENTS.md` available until the migration is verified. If `AGENTS.md` is the only remaining copy, preserve it outside the generated output path before installing.

After installing the package, ask the agent:

```text
Use migration-baseline to port every repository-owned or locally changed rule from the legacy agents/ sources and preserved AGENTS.md. If there are concise rules that must affect nearly every task or prevent unsafe or invalid work, put them in .apm/instructions/project-baseline.instructions.md; otherwise do not create that file. Put detailed or conditional guidance in .apm/skills/project-architecture/SKILL.md and linked references. Do not copy shared guidance or delete the legacy files. Produce a complete parity map.
```

Review the parity map, then run `apm compile --target claude,codex,opencode`, `apm compile --validate --local-only`, and `apm audit` (or the equivalent Task wrappers). Remove the legacy layout only after every old section has a current shared owner or a verified local destination.

## Edit this package

| Change | Source |
| --- | --- |
| Always-on cross-stack guidance | `.apm/instructions/engineering-baseline.instructions.md` |
| Optional consumer-owned critical always-on guidance | `.apm/instructions/project-baseline.instructions.md` in the consuming repository |
| Consumer-owned detailed or conditional guidance | `.apm/skills/project-architecture/` in the consuming repository |
| Shared Python, Django, Vue, framework-testing, AI-generation, or technical-writing conventions | `.apm/skills/<skill-name>/SKILL.md` |
| Long examples and review references | The owning skill's `references/` directory |
| Reusable review and contribution workflows | `.apm/skills/<workflow-name>/SKILL.md` |
| Consumer Task and ignore templates | `templates/` |

### Skill structure

Keep skill frontmatter limited to `name` and a trigger-focused `description`. Use only the sections a skill needs, in this relative order:

| Skill family | Section order |
| --- | --- |
| Implementation guidance | `Scope` → `Workflow` → `Core Guidance` or `Reference Selection` → `Example Selection` → `Completion Checklist` |
| Reviews, audits, and context gathering | `Scope` → `Workflow` → `Reference Selection` → `Review Criteria` → `Output` → `Completion Checklist` → `Maintenance` |

Do not add empty sections merely for uniformity. Keep short, cohesive guidance directly in `SKILL.md`; put detailed rules and long examples in directly linked `references/` files, and tell the agent exactly when each reference should be read. Keep selection and procedural instructions in `SKILL.md`.

Do not edit generated output. Validate a package change with:

```bash
apm compile --validate --local-only
apm audit
```

To release it, update `version` in `apm.yml`, validate, commit, and create the matching Git tag. Consumer repositories install and pin that tag directly.

`apm pack` bundles installed dependencies; it is not the release mechanism for this source package.

## Guidance loading

The shared always-on baseline contains only cross-stack rules and a skill router. A consuming repository may add a concise always-on `project-baseline` when it has critical local facts; an empty baseline should be omitted. Detailed or conditional decisions stay in `project-architecture`. Python guidance stays compact in `python-conventions`; Django, Vue, framework testing, technical writing, review, and contribution workflows use skills that load only when the task needs them.

`django-patterns` and `vue-patterns` own production-code guidance. `django-testing` and `vue-testing` own test structure, coverage, assertions, and verification. Their concise names and descriptions are advertised for discovery; the skill bodies and selected references load only when the request matches them.

Production-only work loads the implementation skill, test-only work loads the testing skill, and tasks that change both implementation and tests load both.

The immutable pre-APM aggregate remains at `.apm/skills/migration-baseline/references/legacy-codex-AGENTS.md` (SHA-256 `2f1ea4481b85236a287645d2bcb83c626559d0060d961f8ea1bb0c1382744b43`) only to distinguish former shared content from repository-owned guidance during a legacy port.
