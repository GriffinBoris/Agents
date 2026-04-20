# Agents

This repo builds installable guidance packages for multiple coding agents.

Authored content, the builder, and installer scripts live in `agents/`.

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
- `agents/tools/`: target-specific static assets such as OpenCode config
- `agents/build_agents.py`: primary build CLI entrypoint
- `agents/agents_builder/`: shared builder package
- `agents/scripts/install-agents.sh`: shell installer
- `agents/scripts/install-agents.ps1`: PowerShell installer
- `dist/`: generated output

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
- `dist/opencode/AGENTS.md`
- `dist/opencode/opencode.json`
- `dist/opencode/.opencode/commands/*.md`
- `dist/opencode/.opencode/skills/*/SKILL.md`
- `dist/claude/AGENTS.md`
- `dist/claude/.claude/CLAUDE.md`
- `dist/claude/.claude/commands/*.md` for Claude-compatible commands
- `dist/claude/.claude/skills/*/SKILL.md`
- `dist/copilot/AGENTS.md`
- `dist/copilot/.github/copilot-instructions.md`
- `dist/codex/AGENTS.md`
- `dist/codex/.agents/skills/*/SKILL.md`
- `dist/gemini/AGENTS.md`
- `dist/gemini/GEMINI.md`
- `dist/gemini/.gemini/commands/*.toml` for Gemini-compatible commands
- `dist/gemini/.gemini/skills/*/SKILL.md`

`AGENTS.md` is the shared root guidance file for all generated targets. Harness-specific files import or complement it from their expected locations.

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

- `opencode`: root `AGENTS.md`, root `opencode.json`, `.opencode/commands/`, `.opencode/skills/`
- `claude`: root `AGENTS.md`, `.claude/CLAUDE.md`, `.claude/commands/`, `.claude/skills/`
- `copilot`: root `AGENTS.md`, `.github/copilot-instructions.md`
- `codex`: root `AGENTS.md`, `.agents/skills/`
- `gemini`: root `AGENTS.md`, root `GEMINI.md`, `.gemini/commands/`, `.gemini/skills/`

Claude reads `.claude/CLAUDE.md`, which imports the shared root `AGENTS.md`. Gemini reads `GEMINI.md`, which imports the shared root `AGENTS.md`.

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

- OpenCode: `dist/.opencode`, `dist/AGENTS.md`, `dist/opencode.json`
- Claude: `dist/.claude`, `dist/AGENTS.md`
- Copilot: `dist/.github/copilot-instructions.md`, `dist/AGENTS.md`
- Codex: `dist/.agents`, `dist/AGENTS.md`
- Gemini: `dist/.gemini`, `dist/GEMINI.md`, `dist/AGENTS.md`
