import shutil
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from agent_flow.store import RUNS_DIRECTORY, RunStore, RunStoreError, atomic_text_write


class InstallerError(RuntimeError):
    pass


def install_repository_assets(repository_root: Path, *, force: bool = False) -> dict:
    root = repository_root.resolve()
    if not root.is_dir():
        raise InstallerError(f'Repository root does not exist: {root}')

    files = _asset_files(root)
    for _, destination in files:
        if not destination.parent.resolve().is_relative_to(root):
            raise InstallerError(f'Project asset path resolves outside the repository: {destination}')
    conflicts = [
        destination
        for source, destination in files
        if destination.is_symlink() or (destination.is_file() and source.read_bytes() != destination.read_bytes())
    ]
    if conflicts and not force:
        relative = ', '.join(str(path.relative_to(root)) for path in conflicts)
        raise InstallerError(
            f'Refusing to overwrite changed project file(s): {relative}. Re-run with --force to replace them'
        )

    installed = []
    unchanged = []
    for source, destination in files:
        if not destination.is_symlink() and destination.is_file() and source.read_bytes() == destination.read_bytes():
            unchanged.append(str(destination.relative_to(root)))
            continue
        atomic_text_write(destination, source.read_text(encoding='utf-8'))
        installed.append(str(destination.relative_to(root)))

    return {
        'repository': str(root),
        'installed': installed,
        'unchanged': unchanged,
        'next_steps': [
            'Invoke $agent-flow from a Codex Desktop task.',
            'Run agent-flow view --repo . to open the live viewer.',
        ],
    }


def diagnose_repository(repository_root: Path) -> dict:
    root = repository_root.resolve()
    if not root.is_dir():
        raise InstallerError(f'Repository root does not exist: {root}')

    skill_path = root / '.agents' / 'skills' / 'agent-flow' / 'SKILL.md'
    workflow_directory = root / '.agents' / 'workflows' / 'agent-flow'
    run_ignore_path = root / '.agent-flow' / '.gitignore'
    skill_ok = not skill_path.is_symlink() and skill_path.parent.resolve().is_relative_to(root) and skill_path.is_file()
    workflows = []
    if workflow_directory.resolve().is_relative_to(root):
        workflows = sorted(
            str(path.relative_to(root))
            for path in workflow_directory.glob('*.yml')
            if path.is_file() and not path.is_symlink()
        )
    try:
        run_ignore_ok = (
            not run_ignore_path.is_symlink()
            and run_ignore_path.parent.resolve().is_relative_to(root)
            and run_ignore_path.is_file()
            and 'runs/' in run_ignore_path.read_text(encoding='utf-8').splitlines()
        )
    except OSError:
        run_ignore_ok = False
    runs_directory = root / RUNS_DIRECTORY
    valid_runs = 0
    invalid_runs = 0
    if runs_directory.is_dir():
        if not runs_directory.resolve().is_relative_to(root):
            invalid_runs = 1
        else:
            for path in runs_directory.iterdir():
                if not path.is_dir():
                    continue
                try:
                    RunStore.open(root, path.name).load_state()
                except RunStoreError:
                    invalid_runs += 1
                else:
                    valid_runs += 1

    checks = {
        'repository': {'ok': True, 'path': str(root)},
        'codex_skill': {'ok': skill_ok, 'path': str(skill_path)},
        'example_workflows': {'ok': bool(workflows), 'paths': workflows},
        'run_storage_ignore': {
            'ok': run_ignore_ok,
            'path': str(run_ignore_path),
        },
        'github_cli': {'ok': shutil.which('gh') is not None, 'required_only_for_issue_intake': True},
        'runs': {'ok': invalid_runs == 0, 'valid': valid_runs, 'invalid': invalid_runs},
    }
    recommendations = []
    if (
        not checks['codex_skill']['ok']
        or not checks['example_workflows']['ok']
        or not checks['run_storage_ignore']['ok']
    ):
        recommendations.append('Run agent-flow init --repo .')
    if not checks['github_cli']['ok']:
        recommendations.append('Install and authenticate gh before using --issue')
    if invalid_runs:
        recommendations.append('Inspect incomplete or corrupt directories under .agent-flow/runs')

    required_checks = ('repository', 'codex_skill', 'example_workflows', 'run_storage_ignore', 'runs')
    return {
        'version': package_version(),
        'python': sys.version.split()[0],
        'healthy': all(checks[name]['ok'] for name in required_checks),
        'checks': checks,
        'recommendations': recommendations,
    }


def _asset_files(repository_root: Path) -> list[tuple[Path, Path]]:
    resource_root = Path(__file__).resolve().parent / 'resources'
    if resource_root.is_dir():
        skill_source = resource_root / 'skill'
        workflow_source = resource_root / 'workflows'
        project_ignore_source = resource_root / 'project.gitignore'
    else:
        source_root = Path(__file__).resolve().parents[2]
        skill_source = source_root / '.apm' / 'skills' / 'agent-flow'
        workflow_source = source_root / 'examples' / 'agent-flow'
        project_ignore_source = source_root / 'templates' / 'agent-flow.gitignore'

    required_sources = [
        skill_source / 'SKILL.md',
        workflow_source / 'deep-feature.yml',
        workflow_source / 'github-issue-to-pr.yml',
        project_ignore_source,
    ]
    missing = [str(path) for path in required_sources if not path.is_file()]
    if missing:
        raise InstallerError(f'Installed package is missing project assets: {", ".join(missing)}')

    sources = [*skill_source.rglob('*'), *workflow_source.glob('*.yml')]
    files = []
    for source in sources:
        if not source.is_file():
            continue
        if source.is_relative_to(skill_source):
            relative = Path('.agents') / 'skills' / 'agent-flow' / source.relative_to(skill_source)
        else:
            relative = Path('.agents') / 'workflows' / 'agent-flow' / source.name
        files.append((source, repository_root / relative))
    files.append((project_ignore_source, repository_root / '.agent-flow' / '.gitignore'))
    return sorted(files, key=lambda item: str(item[1]))


def package_version() -> str:
    try:
        return version('agent-flow-runner')
    except PackageNotFoundError:
        return 'source'
