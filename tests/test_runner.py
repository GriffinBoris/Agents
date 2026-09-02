from pathlib import Path

import pytest

from agent_flow.adapters import AgentResult
from agent_flow.config import parse_workflow
from agent_flow.runner import WorkflowExecutionError, WorkflowRunner
from agent_flow.store import RUNS_DIRECTORY, RunStore


class FakeAdapter:
    def __init__(self, fail_first: bool = False, output: str = ''):
        self.calls = []
        self.fail_first = fail_first
        self.output = output

    def run(self, profile, delegated_profile, step, prompt, repository_root, log_directory):
        self.calls.append(
            {
                'profile': profile,
                'delegated_profile': delegated_profile,
                'step': step,
                'prompt': prompt,
            }
        )
        if self.fail_first and len(self.calls) == 1:
            raise RuntimeError('temporary provider failure')
        return AgentResult(text=self.output or f'output from {step.id}', metadata={})


def test_run_pauses_for_approval_then_resumes(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    request_path = repository / 'source-request.md'
    request_path.write_text('Build the feature.', encoding='utf-8')
    workflow = parse_workflow(_approval_workflow(), repository)
    adapter = FakeAdapter()
    runner = WorkflowRunner(adapters={'codex': adapter})

    store, state = runner.start(workflow, request_path, repository)

    assert state.status == 'waiting_for_approval'
    assert state.waiting_step == 'approve-research'
    assert state.waiting_message == 'Review research.md before continuing.'
    assert state.steps['approve-research']['attempts'] == 1
    assert (store.run_directory / 'research.md').read_text(encoding='utf-8') == 'output from research\n'
    assert str(store.run_directory / 'request.md') in adapter.calls[0]['prompt']

    approved_state = runner.approve(store)
    assert approved_state.status == 'approved'
    assert approved_state.waiting_message is None

    completed_state = runner.resume(store)
    assert completed_state.status == 'completed'
    assert (store.run_directory / 'test-output.txt').read_text(encoding='utf-8').strip() == 'tests passed'
    assert completed_state.steps['research']['metadata']['model'] == 'gpt-5.6-terra'
    assert completed_state.steps['research']['metadata']['provider'] == 'codex'


def test_failed_agent_step_can_be_resumed(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    request_path = repository / 'request-source.md'
    request_path.write_text('Investigate the project.', encoding='utf-8')
    workflow = parse_workflow(_single_agent_workflow(), repository)
    adapter = FakeAdapter(fail_first=True)
    runner = WorkflowRunner(adapters={'codex': adapter})

    with pytest.raises(WorkflowExecutionError, match='temporary provider failure'):
        runner.start(workflow, request_path, repository)

    run_directory = next((repository / RUNS_DIRECTORY).iterdir())
    store = RunStore.open(repository, run_directory.name)
    failed_state = store.load_state()
    assert failed_state.status == 'failed'
    assert failed_state.steps['research']['attempts'] == 1

    completed_state = runner.resume(store)

    assert completed_state.status == 'completed'
    assert completed_state.steps['research']['attempts'] == 2
    assert (run_directory / 'research.md').is_file()


def test_parallel_read_only_agents_write_independent_artifacts(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    request_path = repository / 'request-source.md'
    request_path.write_text('Review the project.', encoding='utf-8')
    workflow_data = _single_agent_workflow()
    first = workflow_data['steps'][0]
    second = {**first, 'id': 'security', 'output': 'security.md'}
    workflow_data['steps'] = [{'id': 'reviews', 'type': 'parallel', 'steps': [first, second]}]
    workflow = parse_workflow(workflow_data, repository)
    adapter = FakeAdapter()

    store, state = WorkflowRunner(adapters={'codex': adapter}).start(workflow, request_path, repository)

    assert state.status == 'completed'
    assert state.steps['reviews']['status'] == 'succeeded'
    assert state.steps['research']['status'] == 'succeeded'
    assert state.steps['security']['status'] == 'succeeded'
    assert (store.run_directory / 'research.md').is_file()
    assert (store.run_directory / 'security.md').is_file()


def test_rejects_agent_output_that_does_not_match_schema(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    request_path = repository / 'request-source.md'
    request_path.write_text('Review the project.', encoding='utf-8')
    workflow_data = _single_agent_workflow()
    workflow_data['steps'][0]['schema'] = {
        'type': 'object',
        'properties': {'status': {'type': 'string'}},
        'required': ['status'],
        'additionalProperties': False,
    }
    workflow = parse_workflow(workflow_data, repository)
    adapter = FakeAdapter(output='{"unexpected": true}')

    with pytest.raises(WorkflowExecutionError, match='does not match its JSON Schema'):
        WorkflowRunner(adapters={'codex': adapter}).start(workflow, request_path, repository)


def _single_agent_workflow() -> dict:
    return {
        'version': 1,
        'name': 'test-workflow',
        'models': {
            'default': {
                'provider': 'codex',
                'model': 'gpt-5.6-terra',
                'effort': 'medium',
            }
        },
        'defaults': {'model': 'default'},
        'steps': [
            {
                'id': 'research',
                'type': 'agent',
                'mode': 'read',
                'prompt': 'Research the request.',
                'inputs': ['request.md'],
                'output': 'research.md',
            }
        ],
    }


def _approval_workflow() -> dict:
    workflow = _single_agent_workflow()
    workflow['steps'].extend(
        [
            {
                'id': 'approve-research',
                'type': 'approval',
                'message': 'Review research.md before continuing.',
            },
            {
                'id': 'tests',
                'type': 'shell',
                'command': ['python3', '-c', "print('tests passed')"],
                'output': 'test-output.txt',
            },
        ]
    )
    return workflow
