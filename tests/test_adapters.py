import json
import subprocess
from pathlib import Path

from agent_flow.adapters import ClaudeAdapter, CodexAdapter
from agent_flow.config import AgentStep, DelegationConfig, ModelProfile


def test_codex_adapter_maps_model_sandbox_schema_and_subagents(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured['command'] = command
        captured['kwargs'] = kwargs
        stdout = '\n'.join(
            [
                json.dumps({'type': 'thread.started', 'thread_id': 'thread-1'}),
                json.dumps(
                    {
                        'type': 'item.completed',
                        'item': {'type': 'agent_message', 'text': '{"summary":"done"}'},
                    }
                ),
                json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 3}}),
            ]
        )
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr='')

    monkeypatch.setattr('agent_flow.adapters.shutil.which', lambda _: '/usr/local/bin/codex')
    monkeypatch.setattr('agent_flow.adapters.subprocess.run', fake_run)
    step = _agent_step(
        schema={'type': 'object'},
        delegation=DelegationConfig('native', 3, 'fast', 'Split the scan by package.'),
    )
    profile = ModelProfile('deep', 'codex', 'gpt-5.6-sol', 'high')
    delegated_profile = ModelProfile('fast', 'codex', 'gpt-5.6-luna', 'medium')

    result = CodexAdapter().run(profile, delegated_profile, step, 'prompt', tmp_path, tmp_path)

    command = captured['command']
    assert command[:2] == ['/usr/local/bin/codex', 'exec']
    assert command[command.index('--model') + 1] == 'gpt-5.6-sol'
    assert 'model_reasoning_effort="high"' in command
    assert 'agents.max_concurrent_threads_per_session=3' in command
    assert 'agents.default_subagent_model="gpt-5.6-luna"' in command
    assert command[command.index('--sandbox') + 1] == 'read-only'
    assert captured['kwargs']['input'] == 'prompt'
    assert result.text == '{"summary":"done"}'
    assert result.metadata['thread_id'] == 'thread-1'
    assert (tmp_path / 'research.schema.json').is_file()


def test_claude_adapter_maps_model_permissions_and_named_subagent(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured['command'] = command
        captured['kwargs'] = kwargs
        response = {
            'structured_output': {'summary': 'done'},
            'session_id': 'session-1',
            'total_cost_usd': 0.1,
        }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(response), stderr='')

    monkeypatch.setattr('agent_flow.adapters.shutil.which', lambda _: '/usr/local/bin/claude')
    monkeypatch.setattr('agent_flow.adapters.subprocess.run', fake_run)
    step = _agent_step(
        schema={'type': 'object'},
        allowed_tools=('Read', 'Grep'),
        delegation=DelegationConfig('native', 2, 'fast', 'Inspect independent modules.'),
    )
    profile = ModelProfile('deep', 'claude', 'opus', 'high')
    delegated_profile = ModelProfile('fast', 'claude', 'haiku', 'low')

    result = ClaudeAdapter().run(profile, delegated_profile, step, 'prompt', tmp_path, tmp_path)

    command = captured['command']
    assert command[:2] == ['/usr/local/bin/claude', '--print']
    assert command[command.index('--model') + 1] == 'opus'
    assert command[command.index('--permission-mode') + 1] == 'plan'
    assert command[command.index('--allowedTools') + 1] == 'Read,Grep'
    agents = json.loads(command[command.index('--agents') + 1])
    assert agents['workflow-worker']['model'] == 'haiku'
    assert agents['workflow-worker']['effort'] == 'low'
    assert captured['kwargs']['input'] == 'prompt'
    assert result.text == '{\n  "summary": "done"\n}'
    assert result.metadata['session_id'] == 'session-1'


def test_claude_adapter_disables_subagents_by_default(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured['command'] = command
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({'result': 'done'}), stderr='')

    monkeypatch.setattr('agent_flow.adapters.shutil.which', lambda _: '/usr/local/bin/claude')
    monkeypatch.setattr('agent_flow.adapters.subprocess.run', fake_run)

    ClaudeAdapter().run(
        ModelProfile('default', 'claude', 'sonnet', 'medium'),
        None,
        _agent_step(),
        'prompt',
        tmp_path,
        tmp_path,
    )

    command = captured['command']
    assert command[command.index('--disallowedTools') + 1] == 'Agent'


def _agent_step(
    schema=None,
    allowed_tools=(),
    delegation=DelegationConfig('off', 0, None, None),
) -> AgentStep:
    return AgentStep(
        id='research',
        type='agent',
        model='deep',
        mode='read',
        prompt='Research.',
        inputs=('request.md',),
        output='research.md',
        schema=schema,
        allowed_tools=allowed_tools,
        delegation=delegation,
    )
