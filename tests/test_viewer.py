import json
import threading
from pathlib import Path
from urllib.request import urlopen

import pytest

from agent_flow.config import parse_workflow
from agent_flow.controller import WorkflowController
from agent_flow.viewer import ViewerError, create_viewer_server


def test_viewer_serves_live_run_data(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()
    workflow = parse_workflow(
        {
            'version': 1,
            'name': 'visual-flow',
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
                    'prompt': 'Inspect the repository.',
                    'inputs': ['request.md'],
                    'output': 'research.md',
                    'delegation': {
                        'strategy': 'native',
                        'max_agents': 2,
                    },
                }
            ],
        }
    )
    store, state = WorkflowController().start_text(workflow, 'Build the viewer.', repository)
    WorkflowController().begin(store, 'research')
    WorkflowController().attach_worker(store, 'research', 'worker-123')

    server = create_viewer_server(repository, run_id=state.run_id, port=0)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    base_url = f'http://127.0.0.1:{server.server_address[1]}'
    try:
        with urlopen(f'{base_url}/', timeout=2) as response:
            html = response.read().decode('utf-8')
            assert response.headers['Cache-Control'] == 'no-store'
        assert '<title>Agent Flow</title>' in html

        with urlopen(f'{base_url}/api/runs', timeout=2) as response:
            listing = json.load(response)
        assert listing['runs'][0]['run_id'] == state.run_id
        assert listing['runs'][0]['status'] == 'running'

        with urlopen(f'{base_url}/api/runs/{state.run_id}', timeout=2) as response:
            detail = json.load(response)
        assert detail['workflow']['name'] == 'visual-flow'
        assert detail['state']['steps']['research']['metadata']['worker_ids'] == ['worker-123']
        assert detail['events'][-1]['type'] == 'worker.attached'
        assert {artifact['path'] for artifact in detail['artifacts']} == {'request.md'}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_viewer_rejects_unknown_run(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()

    with pytest.raises(ViewerError, match='Run does not exist'):
        create_viewer_server(repository, run_id='missing-run', port=0)


def test_viewer_rejects_invalid_port(tmp_path: Path) -> None:
    repository = tmp_path / 'repository'
    repository.mkdir()

    with pytest.raises(ViewerError, match='between 0 and 65535'):
        create_viewer_server(repository, port=70000)
