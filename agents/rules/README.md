# Agents Lint Rule Pack

This directory turns high-confidence guidance into deterministic checks while keeping mature language tools in charge of parsing, formatting, editor integration, and standard rules.

Developers and coding agents get one interface:

```bash
python3 agents/lint_agents.py check
python3 agents/lint_agents.py fix
```

An installed package also exposes `agents-lint check` and `agents-lint fix`.

The wrapper is deliberately small. It reads `.agents-lint.toml`, selects tools whose required project paths exist, runs safe fixes in manifest order, and runs the full check phase again after fixing. Use `--profile backend`, `--profile frontend`, or `--profile custom` to narrow local feedback. CI should run all profiles and may use `--output json` for normalized results.

## Architecture

| Concern | Engine | Ownership |
|---|---|---|
| Python lint and imports | Ruff | `config/ruff.toml` |
| Python formatting | Ruff format | `config/ruff.toml` |
| Vue and TypeScript lint | ESLint, typescript-eslint, eslint-plugin-vue | `config/eslint.config.mjs` |
| Vue and TypeScript formatting | Prettier | `config/prettier.config.mjs` |
| Cross-language structural patterns | ast-grep | `ast-grep/` |
| Loaded Django metadata | Django system checks | `django_checks/` |
| Type correctness | mypy/django-stubs and vue-tsc | target-project configuration |
| Unified command and output | Agents Lint | `agents/agents_linter/` |

The intended execution order is:

1. Apply repository-owned structural rewrites that are explicitly marked safe.
2. Apply standard linter fixes.
3. Run native formatters.
4. Re-run structural checks, linters, format checks, type checks, and Django checks.

Do not create custom formatter printers for repository conventions. Formatting belongs to Ruff and Prettier. A custom rule may include a narrow, deterministic fix, but broader refactors should remain diagnostics or explicit codemods.

## Layout

```text
agents/rules/
  catalog.toml                    stable IDs and guidance links
  config/
    agents-lint.toml              starter command manifest
    eslint.config.mjs             Vue/TypeScript baseline
    prettier.config.mjs           frontend formatting baseline
    ruff.toml                     Python baseline
  ast-grep/
    sgconfig.yml
    rules/                         simple structural checks/rewrites
    tests/                         valid and invalid rule fixtures
  eslint-plugin-agents/
    rules/                         Vue-aware repository rules
    tests/
  django_checks/                   checks requiring Django's app registry
```

## Rule Lifecycle

Every custom rule must have:

- a stable `AGPY`, `AGDJ`, or `AGVUE` ID in `catalog.toml`;
- one primary guidance section and, when available, a named example;
- valid and invalid fixtures;
- a severity and rollout state;
- a fix classification of `safe`, `unsafe`, or `none`;
- a narrow suppression mechanism when legitimate exceptions exist.

New rules should start as `experimental` warnings. Promote them to `active` errors only after running them across representative repositories and eliminating noisy matches. Rules requiring architectural judgment stay in the homogeneity-audit skills instead of this pack.

## Target-Project Setup

1. Copy `config/agents-lint.toml` to the target root as `.agents-lint.toml` and adjust paths or commands.
2. Extend the target Ruff configuration from `agents/rules/config/ruff.toml`, or copy the settings into its existing `pyproject.toml`.
3. Point the frontend ESLint and Prettier scripts at the starter configs, merging with existing project configuration where necessary.
4. Add `agents.rules.django_checks` to `INSTALLED_APPS` to enable `python manage.py check --tag agents`.
5. Install only the engines used by that repository. Optional tools are reported as skipped by the wrapper.

The starter manifest assumes `backend/` and `frontend/` roots. A monorepo can add more `[[tools]]` entries without changing the Python runner.

## Fix Policy

`agents-lint fix` runs only each engine's normal safe-fix command. A rule is eligible for automatic fixing when the replacement is local, deterministic, behavior-preserving, and idempotent. Import boundary violations, ownership scoping, network I/O in model methods, and large API rewrites must remain diagnostics.

Examples of safe fixes include quote/spacing normalization, import sorting, and a precise syntax replacement whose output is covered by fixtures. Examples of unsafe fixes include replacing a direct Axios request with a domain API method or inventing an ownership filter.
