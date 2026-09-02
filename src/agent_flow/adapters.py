import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

from agent_flow.config import AgentStep, ModelProfile


class AdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentResult:
    text: str
    metadata: dict


class AgentAdapter(Protocol):
    def run(
        self,
        profile: ModelProfile,
        delegated_profile: Optional[ModelProfile],
        step: AgentStep,
        prompt: str,
        repository_root: Path,
        log_directory: Path,
    ) -> AgentResult: ...


class CodexAdapter:
    def run(
        self,
        profile: ModelProfile,
        delegated_profile: Optional[ModelProfile],
        step: AgentStep,
        prompt: str,
        repository_root: Path,
        log_directory: Path,
    ) -> AgentResult:
        executable = shutil.which('codex')
        if executable is None:
            raise AdapterError('Codex CLI is not installed or not available on PATH')

        command = [
            executable,
            'exec',
            '--ephemeral',
            '--json',
            '--color',
            'never',
            '--cd',
            str(repository_root),
            '--sandbox',
            'read-only' if step.mode == 'read' else 'workspace-write',
        ]
        if profile.model is not None:
            command.extend(['--model', profile.model])
        if profile.effort is not None:
            command.extend(['--config', _toml_config('model_reasoning_effort', profile.effort)])

        command.extend(self._delegation_arguments(step, delegated_profile))
        if step.schema is not None:
            schema_path = log_directory / f'{step.id}.schema.json'
            schema_path.write_text(json.dumps(step.schema, indent=2) + '\n', encoding='utf-8')
            command.extend(['--output-schema', str(schema_path)])
        command.append('-')

        completed_process = subprocess.run(
            command,
            cwd=repository_root,
            input=prompt,
            capture_output=True,
            text=True,
            check=False,
        )
        (log_directory / f'{step.id}.jsonl').write_text(completed_process.stdout, encoding='utf-8')
        (log_directory / f'{step.id}.stderr.log').write_text(completed_process.stderr, encoding='utf-8')
        if completed_process.returncode != 0:
            raise AdapterError(_process_error('Codex', step.id, completed_process))

        final_text, metadata = _parse_codex_output(completed_process.stdout, step.id)
        return AgentResult(text=final_text, metadata=metadata)

    @staticmethod
    def _delegation_arguments(
        step: AgentStep,
        delegated_profile: Optional[ModelProfile],
    ) -> list[str]:
        arguments = []
        if step.delegation.strategy == 'off':
            return ['--config', 'agents.enabled=false']

        arguments.extend(
            [
                '--config',
                'agents.enabled=true',
                '--config',
                f'agents.max_concurrent_threads_per_session={step.delegation.max_agents}',
            ]
        )
        if delegated_profile is not None and delegated_profile.model is not None:
            arguments.extend(['--config', _toml_config('agents.default_subagent_model', delegated_profile.model)])
        if delegated_profile is not None and delegated_profile.effort is not None:
            arguments.extend(
                [
                    '--config',
                    _toml_config('agents.default_subagent_reasoning_effort', delegated_profile.effort),
                ]
            )
        return arguments


class ClaudeAdapter:
    def run(
        self,
        profile: ModelProfile,
        delegated_profile: Optional[ModelProfile],
        step: AgentStep,
        prompt: str,
        repository_root: Path,
        log_directory: Path,
    ) -> AgentResult:
        executable = shutil.which('claude')
        if executable is None:
            raise AdapterError('Claude Code CLI is not installed or not available on PATH')

        command = [
            executable,
            '--print',
            '--output-format',
            'json',
            '--no-session-persistence',
            '--permission-mode',
            'plan' if step.mode == 'read' else 'acceptEdits',
        ]
        if profile.model is not None:
            command.extend(['--model', profile.model])
        if profile.effort is not None:
            command.extend(['--effort', profile.effort])
        if step.allowed_tools:
            command.extend(['--allowedTools', ','.join(step.allowed_tools)])

        command.extend(self._delegation_arguments(step, delegated_profile))
        if step.schema is not None:
            command.extend(['--json-schema', json.dumps(step.schema, separators=(',', ':'))])

        completed_process = subprocess.run(
            command,
            cwd=repository_root,
            input=prompt,
            capture_output=True,
            text=True,
            check=False,
        )
        (log_directory / f'{step.id}.json').write_text(completed_process.stdout, encoding='utf-8')
        (log_directory / f'{step.id}.stderr.log').write_text(completed_process.stderr, encoding='utf-8')
        if completed_process.returncode != 0:
            raise AdapterError(_process_error('Claude Code', step.id, completed_process))

        try:
            response = json.loads(completed_process.stdout)
        except json.JSONDecodeError as error:
            raise AdapterError(f'Claude Code returned invalid JSON for step {step.id!r}: {error}') from error

        if step.schema is not None:
            output = response.get('structured_output')
            final_text = json.dumps(output, indent=2) if output is not None else ''
        else:
            final_text = response.get('result', '')
        if not isinstance(final_text, str) or not final_text.strip():
            raise AdapterError(f'Claude Code returned an empty result for step {step.id!r}')

        metadata = {
            key: response[key]
            for key in ('duration_ms', 'duration_api_ms', 'num_turns', 'session_id', 'total_cost_usd', 'usage')
            if key in response
        }
        return AgentResult(text=final_text, metadata=metadata)

    @staticmethod
    def _delegation_arguments(
        step: AgentStep,
        delegated_profile: Optional[ModelProfile],
    ) -> list[str]:
        if step.delegation.strategy == 'off':
            return ['--disallowedTools', 'Agent']

        agent_definition = {
            'workflow-worker': {
                'description': 'Handle a bounded, independent workflow subtask and return a concise result.',
                'prompt': step.delegation.instructions
                or 'Complete only the delegated subtask. Return concise findings with exact file references.',
                'permissionMode': 'plan' if step.mode == 'read' else 'acceptEdits',
            }
        }
        worker = agent_definition['workflow-worker']
        if delegated_profile is not None and delegated_profile.model is not None:
            worker['model'] = delegated_profile.model
        if delegated_profile is not None and delegated_profile.effort is not None:
            worker['effort'] = delegated_profile.effort
        if step.allowed_tools:
            worker['tools'] = list(step.allowed_tools)
        return ['--agents', json.dumps(agent_definition, separators=(',', ':'))]


def default_adapters() -> dict[str, AgentAdapter]:
    return {'codex': CodexAdapter(), 'claude': ClaudeAdapter()}


def _parse_codex_output(output: str, step_id: str) -> tuple[str, dict]:
    final_text = ''
    metadata = {}
    for line_number, line in enumerate(output.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise AdapterError(
                f'Codex returned invalid JSONL for step {step_id!r} on line {line_number}: {error}'
            ) from error

        if event.get('type') == 'thread.started':
            metadata['thread_id'] = event.get('thread_id')
        elif event.get('type') == 'turn.completed':
            metadata['usage'] = event.get('usage', {})
        elif event.get('type') == 'item.completed':
            item = event.get('item', {})
            if item.get('type') == 'agent_message':
                final_text = item.get('text', '')

    if not isinstance(final_text, str) or not final_text.strip():
        raise AdapterError(f'Codex returned an empty result for step {step_id!r}')
    return final_text, metadata


def _toml_config(key: str, value: str) -> str:
    return f'{key}={json.dumps(value)}'


def _process_error(provider: str, step_id: str, completed_process: subprocess.CompletedProcess) -> str:
    detail = completed_process.stderr.strip() or completed_process.stdout.strip() or 'no error output'
    return f'{provider} step {step_id!r} exited with code {completed_process.returncode}: {detail}'
