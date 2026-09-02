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


def test_loads_workflow_and_round_trips_snapshot(tmp_path: Path) -> None:
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
    prompt: Research the repository.
    inputs: [request.md]
    output: research.md
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
    assert workflow.model_for(step).model == 'gpt-5.6-sol'
    assert workflow.delegated_model_for(step).model == 'gpt-5.6-luna'

    snapshot_path = tmp_path / 'workflow.json'
    snapshot_path.write_text(json.dumps(workflow_snapshot(workflow)), encoding='utf-8')
    assert load_workflow_snapshot(snapshot_path) == workflow


def test_rejects_non_codex_provider() -> None:
    data = _base_workflow()
    data['models']['claude'] = {'provider': 'claude', 'model': 'sonnet'}

    with pytest.raises(WorkflowConfigError, match='Unsupported provider'):
        parse_workflow(data)


def test_rejects_unknown_model_with_clear_error() -> None:
    data = _base_workflow()
    data['steps'][0]['model'] = 'missing'

    with pytest.raises(WorkflowConfigError, match='Unknown model profile'):
        parse_workflow(data)


def test_parallel_steps_are_limited_to_read_only_agents() -> None:
    data = _base_workflow()
    child = data['steps'][0]
    child['mode'] = 'write'
    data['steps'] = [{'id': 'reviews', 'type': 'parallel', 'steps': [child]}]

    with pytest.raises(WorkflowConfigError, match='must use read mode'):
        parse_workflow(data)


def test_rejects_artifact_paths_that_escape_run_directory() -> None:
    data = _base_workflow()
    data['steps'][0]['output'] = '../outside.md'

    with pytest.raises(WorkflowConfigError, match='safe relative path'):
        parse_workflow(data)


def test_parses_parallel_agent_group() -> None:
    data = _base_workflow()
    first = data['steps'][0]
    second = yaml.safe_load(yaml.safe_dump(first))
    second['id'] = 'security'
    second['output'] = 'security.md'
    data['steps'] = [{'id': 'reviews', 'type': 'parallel', 'steps': [first, second]}]

    workflow = parse_workflow(data)

    step = workflow.steps[0]
    assert isinstance(step, ParallelStep)
    assert [child.id for child in step.steps] == ['research', 'security']


def test_shipped_github_issue_workflow_is_valid() -> None:
    repository_root = Path(__file__).resolve().parents[1]

    workflow = load_workflow(repository_root / 'examples' / 'agent-flow' / 'github-issue-to-pr.yml')

    assert workflow.name == 'github-issue-to-pr'
    assert workflow.steps[0].id == 'gather-context'
    assert workflow.steps[-1].id == 'create-pr'


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
