import json
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
