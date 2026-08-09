# Agents

Shared engineering guidance for Codex, Claude Code, OpenCode, Copilot, and Gemini. Install a pinned release with [APM](https://github.com/microsoft/apm); use skills and examples when a task needs them.

## Use it in a project

Install APM **v0.28.0+** and [Task](https://taskfile.dev), then keep repository-only guidance in a local skill before installing the shared package:

```text
.apm/skills/project-architecture/SKILL.md
```

Give that file Agent Skills frontmatter with `name: project-architecture`, followed by the project's architecture, commands, and tooling guidance. This prevents package upgrades from overwriting project-specific rules.

Download the two ready-made templates from a tagged release. Append the ignore snippet once; do not replace the project's existing `.gitignore`.

```bash
mkdir -p tasks
curl -fsSL https://raw.githubusercontent.com/GriffinBoris/Agents/v0.1.0/templates/tasks/ai.yml -o tasks/ai.yml
curl -fsSL https://raw.githubusercontent.com/GriffinBoris/Agents/v0.1.0/templates/gitignore.apm >> .gitignore
```

Add the Task namespace to the project's `Taskfile.yml`:

```yaml
includes:
  ai:
    taskfile: ./tasks/ai.yml
    dir: .
```

Then run:

```bash
task ai:install
task ai:check
```

The included task file provides these commands:

| Command | Purpose |
| --- | --- |
| `task ai:install` | Initialize APM if needed, install the pinned guidance package, and compile outputs. |
| `task ai:generate` | Rebuild generated harness files after a local guidance change. |
| `task ai:check` | Validate local guidance and detect installed-package drift. |
| `task ai:setup` | Alias for `install`. |

Generated `AGENTS.md`, harness directories, and `apm_modules/` stay ignored. Commit the consumer's `apm.yml`, `apm.lock.yaml`, and local `.apm/skills/project-architecture/` source instead.

The template defaults to Codex, Claude Code, and OpenCode. Override its package or targets when needed:

```bash
AGENTS_PACKAGE=GriffinBoris/Agents#v0.2.0 task ai:install  # upgrade to a reviewed release
APM_TARGETS=claude,codex,opencode,copilot,gemini task ai:install
```

There is no separate pull or merge command. `task ai:install` resolves the chosen package version, recompiles generated files, and `task ai:check` verifies the result.

For a private package, authenticate with a GitHub token that has repository read access:

```bash
export GITHUB_APM_PAT="<token>"
task ai:install
```

## Edit this package

| Change | Source |
| --- | --- |
| Always-on cross-stack guidance | `.apm/instructions/engineering-baseline.instructions.md` |
| Shared Python, Django, Vue, or AI-generation conventions | `.apm/skills/<skill-name>/SKILL.md` |
| Long examples and review references | The owning skill's `references/` directory |
| Reusable commands | `.apm/prompts/` |
| Consumer Task and ignore templates | `templates/` |

Do not edit generated output. Validate a package change with:

```bash
apm compile --validate --local-only
apm audit
```

To release it, update `version` in `apm.yml`, validate, commit, and create the matching Git tag. Consumer repositories install and pin that tag directly.

```bash
apm compile --validate --local-only
apm audit
```

`apm pack` bundles installed dependencies; it is not the release mechanism for this source package.

## Guidance loading

The always-on baseline contains only cross-stack rules and a skill router. Python guidance stays compact in `python-conventions`; Django and Vue guidance use small routing skills that load detailed references and examples only when the task needs them. Consumer-repository decisions remain in that repository's local `project-architecture` skill.

No migration data was discarded. The immutable pre-APM aggregate is retained at `.apm/skills/migration-baseline/references/legacy-codex-AGENTS.md` (SHA-256 `2f1ea4481b85236a287645d2bcb83c626559d0060d961f8ea1bb0c1382744b43`) for parity audits.
