# Agents

This repo builds installable guidance packages for multiple coding agents.

Authored content, the builder, and installer scripts live in `agents/`.

It also includes an experimental, unified lint rule pack. The rule pack delegates standard linting and formatting to Ruff, ESLint, Prettier, Django checks, and type checkers, while repository-specific Python rules and refactors use LibCST. Developers and agents still get one `check`/`fix` interface. See [`agents/rules/README.md`](agents/rules/README.md) for the architecture, starter configuration, rule catalog, and rollout policy.

## Quick Start

macOS:

```bash
curl -fsSL https://raw.githubusercontent.com/GriffinBoris/Agents/main/agents/scripts/install-agents.sh | bash -s -- --target source --dest .
python3 agents/build_agents.py --target opencode --out dist --clean
```

Windows:

```powershell
$script = Join-Path $env:TEMP 'install-agents.ps1'
Invoke-WebRequest https://raw.githubusercontent.com/GriffinBoris/Agents/main/agents/scripts/install-agents.ps1 -OutFile $script
pwsh -File $script -Target source -Dest .
python agents/build_agents.py --target opencode --out dist --clean
```

That OpenCode build writes a packaged output to `dist/opencode/`. If you want the OpenCode files written directly into the current working directory, use `--out . --layout in-place` instead.

## Repository Layout

- `agents/guidance/`: authored modular guidance packages and examples
- `agents/content/commands/`: authored command assets
- `agents/content/skills/`: authored skill assets
- `agents/rules/`: unified lint runner configuration and repository-owned rule pack
- `agents/tools/`: target-specific static assets such as OpenCode config
- `agents/build_agents.py`: primary build CLI entrypoint
- `agents/agents_builder/`: shared builder package
- `agents/scripts/install-agents.sh`: shell installer
- `agents/scripts/install-agents.ps1`: PowerShell installer
- `dist/`: generated output

## Lint Rule Pack

Run the repository's checks through the unified command:

```bash
python3 agents/lint_agents.py check --config .agents-lint.toml
python3 agents/lint_agents.py fix --config .agents-lint.toml
```

If a target project has no `.agents-lint.toml`, the command uses the bundled starter manifest. That manifest discovers conventional `backend/` and `frontend/` project areas and skips tools for areas that are absent. An installed package exposes the same interface as `agents-lint check` and `agents-lint fix`.

The starter implementation includes:

- a stable catalog linking machine rule IDs to guidance and examples;
- shared Ruff, ESLint, and Prettier configuration;
- Python-authored LibCST rules, suppressions, diagnostics, and safe refactors;
- an ESLint plugin for Vue import boundaries and SFC structure;
- a Django system check for audited model admin registration;
- normalized text or JSON orchestration output and automatic post-fix verification.

## Build Locally

Build one target:

```bash
python3 agents/build_agents.py --target opencode --out dist --clean
```

That default uses the packaged layout, so OpenCode output lands in `dist/opencode/...`.

Build all generated targets:

```bash
python3 agents/build_agents.py --target all --out dist --clean
```

Write a single target directly into the output root instead of `dist/<target>/...`:

```bash
python3 agents/build_agents.py --target opencode --out dist --layout in-place --clean
```

That produces `dist/.opencode`, `dist/AGENTS.md`, and any other root-level files for the selected target.

Build the source package snapshot:

```bash
python3 agents/build_agents.py --target source --out dist --clean
```

### CLI Options

- `--target source|opencode|claude|copilot|codex|gemini|all`
- `--out <path>`: output directory root, defaults to `dist`; relative paths resolve from the directory where you run the command
- `--layout packaged|in-place`: `packaged` is the default and writes `dist/<target>/...`; `in-place` writes one non-source target directly into `--out`
- `--clean`: remove each built target output directory before rebuilding it
- `--include-examples`: embed full example bodies in generated instruction files
- `--metadata-only`: include example metadata only, which is the default behavior

## Targets

- `source`
- `opencode`
- `claude`
- `copilot`
- `codex`
- `gemini`

## Generated Outputs

- `dist/source/agents/`
- `dist/opencode/.opencode/AGENTS.md`
- `dist/opencode/opencode.json`
- `dist/opencode/.opencode/commands/*.md`
- `dist/opencode/.opencode/skills/*/SKILL.md`
- `dist/claude/.claude/CLAUDE.md`
- `dist/claude/.claude/commands/*.md` for Claude-compatible commands
- `dist/claude/.claude/skills/*/SKILL.md`
- `dist/copilot/AGENTS.md`
- `dist/copilot/.github/copilot-instructions.md`
- `dist/codex/.agents/AGENTS.md`
- `dist/codex/.codex/config.toml`
- `dist/codex/.agents/skills/*/SKILL.md` for command workflows converted to Codex skills
- `dist/codex/.agents/skills/*/SKILL.md`
- `dist/gemini/.gemini/GEMINI.md`
- `dist/gemini/.gemini/commands/*.toml` for Gemini-compatible commands
- `dist/gemini/.gemini/skills/*/SKILL.md`

The same authored guidance is rendered into each harness's target directory. OpenCode reads `.opencode/AGENTS.md` through root `opencode.json`; Claude reads `.claude/CLAUDE.md`; Codex reads `.agents/AGENTS.md` through `.codex/config.toml`; Gemini reads `.gemini/GEMINI.md`.

## Install The Source Package

Use this when you want the authored guidance plus the local builder so you can generate targets in another repo.

This installs:

- `agents/`

The installer copies only the `agents/` tree directly from the repo. It does not depend on `dist/source`.

### Shell

Install from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/GriffinBoris/Agents/main/agents/scripts/install-agents.sh | bash -s -- --target source --dest .
```

Install from a local checkout:

```bash
bash agents/scripts/install-agents.sh --target source --dest /path/to/project --repo /path/to/Agents
```

Then build a target in the destination repo:

```bash
python3 agents/build_agents.py --target codex --out dist --clean
```

### PowerShell

Install from GitHub:

```powershell
$script = Join-Path $env:TEMP 'install-agents.ps1'
Invoke-WebRequest https://raw.githubusercontent.com/GriffinBoris/Agents/main/agents/scripts/install-agents.ps1 -OutFile $script
pwsh -File $script -Target source -Dest .
```

Install from a local checkout:

```powershell
pwsh -File agents/scripts/install-agents.ps1 -Target source -Dest C:\path\to\project -Repo C:\path\to\Agents
```

Then build a target in the destination repo:

```powershell
python agents/build_agents.py --target codex --out dist --clean
```

## Install A Built Target

Use this when you want to copy a prebuilt target package into another repo without installing the full source builder.

Installers merge into the destination by default. Matching file paths are overwritten, and unrelated existing files are left in place.

Build the target first:

```bash
python3 agents/build_agents.py --target opencode --out dist --clean
```

### Shell

```bash
bash agents/scripts/install-agents.sh --target opencode --dest /path/to/project --repo /path/to/Agents
```

Supported built-target values are:

- `opencode`
- `claude`
- `copilot`
- `codex`
- `gemini`

### PowerShell

```powershell
pwsh -File agents/scripts/install-agents.ps1 -Target opencode -Dest C:\path\to\project -Repo C:\path\to\Agents
```

## Installer Options

Both installers support:

- `--target` or `-Target`: required target name
- `--dest` or `-Dest`: destination root, defaults to the current directory
- `--ref` or `-Ref`: Git ref to download, defaults to `main`
- `--repo` or `-Repo`: GitHub repo slug, GitHub URL, or local checkout path
- `--force` or `-Force`: accepted for compatibility; installs already overwrite matching files by default

## Target Layouts

- `opencode`: root `opencode.json`, `.opencode/AGENTS.md`, `.opencode/commands/`, `.opencode/skills/`
- `claude`: `.claude/CLAUDE.md`, `.claude/commands/`, `.claude/skills/`
- `copilot`: root `AGENTS.md`, `.github/copilot-instructions.md`
- `codex`: `.agents/AGENTS.md`, `.agents/skills/` containing both authored skills and converted command workflows, and `.codex/config.toml`
- `gemini`: `.gemini/GEMINI.md`, `.gemini/commands/`, `.gemini/skills/`

Claude and Gemini read the complete generated guidance directly from `.claude/CLAUDE.md` and `.gemini/GEMINI.md`, respectively.

Target paths are case-sensitive and follow the tools' documented discovery conventions:

- Claude supports `.claude/CLAUDE.md` for project guidance and `.claude/` for project commands and skills. Custom subagents, when authored, belong in `.claude/agents/`.
- OpenCode reads `.opencode/AGENTS.md` through the `instructions` entry in root `opencode.json`; `.opencode/` also contains commands, skills, and custom agents.
- Codex reads `.agents/AGENTS.md` through the fallback configured in `.codex/config.toml`; `.agents/skills/` contains repository skills. The builder converts authored command workflows into Codex skills because Codex does not document a repository custom-command directory.
- Gemini supports `.gemini/GEMINI.md` for project guidance; its commands and skills also remain under `.gemini/`.

## Typical Workflows

### Authoring And Building In This Repo

1. Edit content under `agents/`
2. Run `python3 agents/build_agents.py --target all --out dist --clean`
3. Inspect the generated files in `dist/`

### Reusing The Builder In Another Repo

1. Install `source`
2. Run `python3 agents/build_agents.py --target <target> --out dist --clean` in that repo

### Shipping A Ready-Made Target

1. Build a target in this repo
2. Install that target into the destination repo with one of the installer scripts

### Refresh Guidance In Place

1. Pick one target such as `opencode` or `claude`
2. Run `python3 agents/build_agents.py --target <target> --out . --layout in-place --clean`
3. Commit the refreshed root files and dot-folder content

Examples using `dist` as the output root:

```bash
python3 agents/build_agents.py --target opencode --out dist --layout in-place --clean
python3 agents/build_agents.py --target claude --out dist --layout in-place --clean
python3 agents/build_agents.py --target copilot --out dist --layout in-place --clean
python3 agents/build_agents.py --target codex --out dist --layout in-place --clean
python3 agents/build_agents.py --target gemini --out dist --layout in-place --clean
```

These produce layouts like:

- OpenCode: `dist/.opencode`, `dist/opencode.json`
- Claude: `dist/.claude`
- Copilot: `dist/.github/copilot-instructions.md`, `dist/AGENTS.md`
- Codex: `dist/.agents`, `dist/.codex`
- Gemini: `dist/.gemini`
