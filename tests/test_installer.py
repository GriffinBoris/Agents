from pathlib import Path

import pytest

from agent_flow.installer import InstallerError, diagnose_repository, install_repository_assets


def test_installs_plain_project_files_without_symlinks(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()

    result = install_repository_assets(repository)

    skill = repository / '.agents' / 'skills' / 'agent-flow' / 'SKILL.md'
    workflow = repository / '.agents' / 'workflows' / 'agent-flow' / 'github-issue-to-pr.yml'
    run_ignore = repository / '.agent-flow' / '.gitignore'
    assert skill.is_file() and not skill.is_symlink()
    assert workflow.is_file() and not workflow.is_symlink()
    assert run_ignore.read_text(encoding='utf-8') == 'runs/\n'
    assert str(skill.relative_to(repository)) in result['installed']
    assert install_repository_assets(repository)['installed'] == []


def test_refuses_to_overwrite_project_changes_without_force(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    install_repository_assets(repository)
    skill = repository / '.agents' / 'skills' / 'agent-flow' / 'SKILL.md'
    skill.write_text('team-owned change\n', encoding='utf-8')

    with pytest.raises(InstallerError, match='Refusing to overwrite'):
        install_repository_assets(repository)

    assert skill.read_text(encoding='utf-8') == 'team-owned change\n'
    install_repository_assets(repository, force=True)
    assert skill.read_text(encoding='utf-8').startswith('---\nname: agent-flow')


def test_doctor_reports_installed_assets_and_runs(tmp_path: Path, monkeypatch) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    install_repository_assets(repository)
    monkeypatch.setattr('agent_flow.installer.shutil.which', lambda command: f'/usr/bin/{command}')

    report = diagnose_repository(repository)

    assert report['healthy'] is True
    assert report['checks']['codex_skill']['ok'] is True
    assert len(report['checks']['example_workflows']['paths']) == 2


def test_installer_rejects_project_asset_directory_symlink(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (repository / '.agents').symlink_to(outside, target_is_directory=True)

    with pytest.raises(InstallerError, match='resolves outside the repository'):
        install_repository_assets(repository)
