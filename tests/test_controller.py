import subprocess
from pathlib import Path

import pytest

from agent_flow.config import parse_workflow
from agent_flow.controller import WorkflowController, WorkflowStateError
from agent_flow.store import RUNS_DIRECTORY, RunStore, RunStoreError


def test_parent_driven_run_pauses_for_approval_then_executes_shell(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    request_path = repository / 'source-request.md'
    request_path.write_text('Build the feature.', encoding='utf-8')
    workflow = parse_workflow(_approval_workflow())
    controller = WorkflowController()

    store, state = controller.start(workflow, request_path, repository)

    assert state.status == 'ready'
    descriptor = controller.describe(workflow, store, state)['step']
    assert descriptor['id'] == 'research'
    assert descriptor['model']['model'] == 'gpt-5.6-terra'
    assert descriptor['inputs'][0]['path'] == str(store.run_directory / 'request.md')

    state = controller.begin(store, 'research')
    assert state.status == 'running'
    state = controller.attach_worker(store, 'research', 'worker-123')
    assert state.steps['research']['metadata']['worker_ids'] == ['worker-123']
    store.write_artifact('research.md', 'Research result')

    state = controller.complete(store, 'research')

    assert state.status == 'waiting_for_approval'
    assert state.waiting_step == 'approve-research'
    assert state.steps['research']['metadata']['artifact'] == str(store.run_directory / 'research.md')

    state = controller.approve(store)
    assert state.status == 'ready'
    assert controller.describe(workflow, store, state)['step']['id'] == 'tests'

    state = controller.run_shell(store, 'tests')

    assert state.status == 'completed'
    assert (store.run_directory / 'test-output.txt').read_text(encoding='utf-8').strip() == 'tests passed'


def test_failed_worker_step_can_be_retried_without_launching_a_provider(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    request_path = repository / 'request-source.md'
    request_path.write_text('Investigate the project.', encoding='utf-8')
    workflow = parse_workflow(_single_agent_workflow())
    controller = WorkflowController()

    store, _ = controller.start(workflow, request_path, repository)
    controller.begin(store, 'research')
    failed = controller.fail(store, 'research', 'worker stopped')

    assert failed.status == 'failed'
    assert failed.steps['research']['attempts'] == 1

    controller.begin(store, 'research')
    store.write_artifact('research.md', 'Recovered result')
    completed = controller.complete(store, 'research')

    assert completed.status == 'completed'
    assert completed.steps['research']['attempts'] == 2


def test_retry_requires_a_fresh_artifact_for_the_current_attempt(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    workflow = parse_workflow(_single_agent_workflow())
    controller = WorkflowController()
    store, _ = controller.start_text(workflow, 'Investigate the project.', repository)
    store.write_artifact('research.md', 'Stale result')

    controller.begin(store, 'research')

    with pytest.raises(WorkflowStateError, match='predates the current attempt'):
        controller.complete(store, 'research')

    store.write_artifact('research.md', 'Fresh result')
    assert controller.complete(store, 'research').status == 'completed'


def test_parallel_workers_and_artifacts_are_tracked_independently(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    request_path = repository / 'request-source.md'
    request_path.write_text('Review the project.', encoding='utf-8')
    workflow_data = _single_agent_workflow()
    first = workflow_data['steps'][0]
    second = {**first, 'id': 'security', 'output': 'security.md'}
    workflow_data['steps'] = [{'id': 'reviews', 'type': 'parallel', 'steps': [first, second]}]
    workflow = parse_workflow(workflow_data)
    controller = WorkflowController()

    store, _ = controller.start(workflow, request_path, repository)
    controller.begin(store, 'reviews')
    controller.attach_worker(store, 'research', 'worker-research')
    controller.attach_worker(store, 'security', 'worker-security')
    store.write_artifact('research.md', 'Correctness review')
    store.write_artifact('security.md', 'Security review')

    state = controller.complete(store, 'reviews')

    assert state.status == 'completed'
    assert state.steps['reviews']['status'] == 'succeeded'
    assert state.steps['research']['metadata']['worker_ids'] == ['worker-research']
    assert state.steps['security']['metadata']['worker_ids'] == ['worker-security']


def test_nested_workers_preserve_parentage_and_delegated_model(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    workflow_data = _single_agent_workflow()
    workflow_data['models']['fast'] = {
        'provider': 'codex',
        'model': 'gpt-5.6-luna',
        'effort': 'medium',
    }
    workflow_data['steps'][0]['delegation'] = {
        'strategy': 'native',
        'max_agents': 2,
        'default_model': 'fast',
    }
    workflow = parse_workflow(workflow_data)
    controller = WorkflowController()
    store, _ = controller.start_text(workflow, 'Review the project.', repository)
    controller.begin(store, 'research')

    controller.attach_worker(store, 'research', '/root/research')
    state = controller.attach_worker(
        store,
        'research',
        '/root/research/security',
        parent_worker_id='/root/research',
    )
    controller.attach_worker(
        store,
        'research',
        '/root/research/tests',
        parent_worker_id='/root/research',
    )

    with pytest.raises(WorkflowStateError, match='maximum of 2'):
        controller.attach_worker(
            store,
            'research',
            '/root/research/docs',
            parent_worker_id='/root/research',
        )

    workers = state.steps['research']['metadata']['workers']
    assert workers[0]['model']['profile'] == 'default'
    assert workers[1]['parent_worker_id'] == '/root/research'
    assert workers[1]['model']['profile'] == 'fast'


def test_nested_worker_rejects_unknown_parent(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    workflow = parse_workflow(_single_agent_workflow())
    controller = WorkflowController()
    store, _ = controller.start_text(workflow, 'Review the project.', repository)
    controller.begin(store, 'research')

    with pytest.raises(WorkflowStateError, match='Parent worker'):
        controller.attach_worker(store, 'research', 'child', parent_worker_id='missing')


def test_shell_failure_is_recorded_for_desktop_parent_to_handle(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    request_path = repository / 'request-source.md'
    request_path.write_text('Run validation.', encoding='utf-8')
    workflow_data = _single_agent_workflow()
    workflow_data['steps'] = [{'id': 'tests', 'type': 'shell', 'command': ['python3', '-c', 'raise SystemExit(4)']}]
    workflow = parse_workflow(workflow_data)
    controller = WorkflowController()

    store, _ = controller.start(workflow, request_path, repository)

    with pytest.raises(WorkflowStateError, match='code 4'):
        controller.run_shell(store, 'tests')

    state = store.load_state()
    assert state.status == 'failed'
    assert state.steps['tests']['error'] is not None
    assert (store.log_directory / 'tests.log').is_file()


def test_shell_step_cannot_be_advanced_without_running_command(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    request_path = repository / 'request-source.md'
    request_path.write_text('Run validation.', encoding='utf-8')
    workflow_data = _single_agent_workflow()
    workflow_data['steps'] = [{'id': 'tests', 'type': 'shell', 'command': ['python3', '-c', 'print(1)']}]
    workflow = parse_workflow(workflow_data)
    controller = WorkflowController()

    store, _ = controller.start(workflow, request_path, repository)

    with pytest.raises(WorkflowStateError, match='shell command'):
        controller.begin(store, 'tests')

    assert store.load_state().status == 'ready'


def test_shell_timeout_is_logged_and_marks_step_failed(tmp_path: Path, monkeypatch) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    workflow_data = _single_agent_workflow()
    workflow_data['steps'] = [
        {
            'id': 'tests',
            'type': 'shell',
            'command': ['slow-command'],
            'timeout_seconds': 5,
        }
    ]
    workflow = parse_workflow(workflow_data)
    controller = WorkflowController()
    store, _ = controller.start_text(workflow, 'Run validation.', repository)

    def time_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs['timeout'], output='partial output')

    monkeypatch.setattr('agent_flow.controller.subprocess.run', time_out)

    with pytest.raises(WorkflowStateError, match='timed out after 5 seconds'):
        controller.run_shell(store, 'tests')

    state = store.load_state()
    assert state.status == 'failed'
    assert 'partial output' in (store.log_directory / 'tests.log').read_text(encoding='utf-8')


def test_missing_shell_executable_marks_step_failed(tmp_path: Path, monkeypatch) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    workflow_data = _single_agent_workflow()
    workflow_data['steps'] = [{'id': 'tests', 'type': 'shell', 'command': ['missing-command']}]
    workflow = parse_workflow(workflow_data)
    controller = WorkflowController()
    store, _ = controller.start_text(workflow, 'Run validation.', repository)

    def missing(*args, **kwargs):
        raise FileNotFoundError('missing-command was not found')

    monkeypatch.setattr('agent_flow.controller.subprocess.run', missing)

    with pytest.raises(WorkflowStateError, match='Cannot execute command'):
        controller.run_shell(store, 'tests')

    assert store.load_state().status == 'failed'


def test_store_can_reopen_desktop_managed_run(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    request_path = repository / 'request-source.md'
    request_path.write_text('Keep durable state.', encoding='utf-8')
    workflow = parse_workflow(_single_agent_workflow())

    store, state = WorkflowController().start(workflow, request_path, repository)
    reopened = RunStore.open(repository, state.run_id)

    assert reopened.run_directory == next((repository / RUNS_DIRECTORY).iterdir()).resolve()
    assert reopened.load_state().status == 'ready'


def test_store_rejects_runs_directory_symlink_that_escapes_repository(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (repository / '.agent-flow').symlink_to(outside, target_is_directory=True)

    with pytest.raises(RunStoreError, match='resolves outside the repository'):
        WorkflowController().start_text(parse_workflow(_single_agent_workflow()), 'Inspect.', repository)


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
