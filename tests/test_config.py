import json
from pathlib import Path

import pytest
import yaml

from agent_flow.config import (
    AgentStep,
    ParallelStep,
    WorkflowConfigError,
    load_workflow,
    load_workflow_snapshot,
    parse_workflow,
    workflow_snapshot,
)


def test_loads_workflow_files_and_round_trips_snapshot(tmp_path: Path) -> None:
    (tmp_path / 'prompts').mkdir()
    (tmp_path / 'prompts' / 'research.md').write_text('Research the repository.', encoding='utf-8')
    (tmp_path / 'schemas').mkdir()
    (tmp_path / 'schemas' / 'result.json').write_text(
        json.dumps({'type': 'object', 'properties': {'summary': {'type': 'string'}}}),
        encoding='utf-8',
    )
    workflow_path = tmp_path / 'workflow.yml'
    workflow_path.write_text(
        """version: 1
name: deep-feature
models:
  deep:
    provider: codex
    model: gpt-5.6-sol
    effort: high
  fast:
    provider: codex
    model: gpt-5.6-luna
    effort: medium
defaults:
  model: deep
steps:
  - id: research
    type: agent
    prompt_file: prompts/research.md
    inputs: [request.md]
    output: research.json
    schema_file: schemas/result.json
    delegation:
      strategy: native
      max_agents: 3
      default_model: fast
""",
        encoding='utf-8',
    )

    workflow = load_workflow(workflow_path)

    step = workflow.steps[0]
    assert isinstance(step, AgentStep)
    assert step.prompt == 'Research the repository.'
    assert step.schema == {'type': 'object', 'properties': {'summary': {'type': 'string'}}}
    assert workflow.model_for(step).model == 'gpt-5.6-sol'
    assert workflow.delegated_model_for(step).model == 'gpt-5.6-luna'

    snapshot_path = tmp_path / 'workflow.json'
    snapshot_path.write_text(json.dumps(workflow_snapshot(workflow)), encoding='utf-8')
    assert load_workflow_snapshot(snapshot_path) == workflow


def test_rejects_non_codex_provider(tmp_path: Path) -> None:
    data = _base_workflow()
    data['models']['claude'] = {'provider': 'claude', 'model': 'sonnet'}

    with pytest.raises(WorkflowConfigError, match='Unsupported provider'):
        parse_workflow(data, tmp_path)


def test_rejects_unknown_model_with_clear_error(tmp_path: Path) -> None:
    data = _base_workflow()
    data['steps'][0]['model'] = 'missing'

    with pytest.raises(WorkflowConfigError, match='Unknown model profile'):
        parse_workflow(data, tmp_path)


def test_parallel_steps_are_limited_to_read_only_agents(tmp_path: Path) -> None:
    data = _base_workflow()
    child = data['steps'][0]
    child['mode'] = 'write'
    data['steps'] = [{'id': 'reviews', 'type': 'parallel', 'steps': [child]}]

    with pytest.raises(WorkflowConfigError, match='must use read mode'):
        parse_workflow(data, tmp_path)


def test_rejects_artifact_paths_that_escape_run_directory(tmp_path: Path) -> None:
    data = _base_workflow()
    data['steps'][0]['output'] = '../outside.md'

    with pytest.raises(WorkflowConfigError, match='safe relative path'):
        parse_workflow(data, tmp_path)


def test_rejects_invalid_json_schema_before_run(tmp_path: Path) -> None:
    data = _base_workflow()
    data['steps'][0]['schema'] = {'type': 'not-a-json-schema-type'}

    with pytest.raises(WorkflowConfigError, match='Invalid JSON schema'):
        parse_workflow(data, tmp_path)


def test_parses_parallel_agent_group(tmp_path: Path) -> None:
    data = _base_workflow()
    first = data['steps'][0]
    second = yaml.safe_load(yaml.safe_dump(first))
    second['id'] = 'security'
    second['output'] = 'security.md'
    data['steps'] = [{'id': 'reviews', 'type': 'parallel', 'steps': [first, second]}]

    workflow = parse_workflow(data, tmp_path)

    step = workflow.steps[0]
    assert isinstance(step, ParallelStep)
    assert [child.id for child in step.steps] == ['research', 'security']


def _base_workflow() -> dict:
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
