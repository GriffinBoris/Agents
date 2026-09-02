import json
import subprocess
from pathlib import Path

from agent_flow.cli import main
from agent_flow.store import RunStore


def test_cli_exposes_parent_driven_step_lifecycle(tmp_path: Path, capsys) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    request = repository / 'request.md'
    request.write_text('Inspect the repository.', encoding='utf-8')
    workflow = repository / 'workflow.yml'
    workflow.write_text(
        """version: 1
name: desktop-flow
models:
  default:
    provider: codex
    model: gpt-5.6-terra
    effort: medium
defaults:
  model: default
steps:
  - id: research
    type: agent
    mode: read
    prompt: Inspect the request.
    inputs: [request.md]
    output: research.md
""",
        encoding='utf-8',
    )

    assert main(['start', str(workflow), '--request', str(request), '--repo', str(repository)]) == 0
    started = json.loads(capsys.readouterr().out)
    run_id = started['run_id']
    assert started['status'] == 'ready'
    assert started['step']['model']['model'] == 'gpt-5.6-terra'

    assert main(['begin', run_id, 'research', '--repo', str(repository)]) == 0
    capsys.readouterr()
    assert main(['attach', run_id, 'research', 'worker-1', '--repo', str(repository)]) == 0
    capsys.readouterr()

    store = RunStore.open(repository, run_id)
    store.write_artifact('research.md', 'Findings')

    assert main(['complete', run_id, 'research', '--repo', str(repository)]) == 0
    completed = json.loads(capsys.readouterr().out)
    assert completed['status'] == 'completed'
    assert completed['step'] is None


def test_cli_can_use_github_issue_as_request(tmp_path: Path, capsys, monkeypatch) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    workflow = repository / 'workflow.yml'
    workflow.write_text(
        """version: 1
name: issue-flow
models:
  default:
    provider: codex
    model: gpt-5.6-terra
    effort: medium
defaults:
  model: default
steps:
  - id: research
    type: agent
    prompt: Inspect the issue.
    inputs: [request.md]
    output: research.md
""",
        encoding='utf-8',
    )
    issue_payload = {
        'number': 42,
        'title': 'Keep the parent visible',
        'body': 'Use native subagents.',
        'url': 'https://github.com/example/project/issues/42',
        'state': 'OPEN',
        'labels': [{'name': 'enhancement'}],
        'assignees': [{'login': 'octocat'}],
    }

    def fake_run(command, **kwargs):
        assert command[:3] == ['gh', 'issue', 'view']
        assert command[3] == 'https://github.com/example/project/issues/42'
        assert kwargs['cwd'] == repository.resolve()
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(issue_payload), stderr='')

    monkeypatch.setattr('agent_flow.cli.subprocess.run', fake_run)

    assert (
        main(
            [
                'start',
                str(workflow),
                '--issue',
                issue_payload['url'],
                '--repo',
                str(repository),
            ]
        )
        == 0
    )
    started = json.loads(capsys.readouterr().out)
    request = Path(started['run_directory']) / 'request.md'

    assert '# GitHub Issue #42: Keep the parent visible' in request.read_text(encoding='utf-8')
    assert 'Use native subagents.' in request.read_text(encoding='utf-8')
