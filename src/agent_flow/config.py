import json
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Optional, Union

import yaml

SUPPORTED_PROVIDERS = {'codex'}
SUPPORTED_STEP_TYPES = {'agent', 'approval', 'parallel', 'shell'}
SUPPORTED_DELEGATION_STRATEGIES = {'native', 'off'}
SUPPORTED_MODES = {'read', 'write'}


class WorkflowConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ModelProfile:
    name: str
    provider: str
    model: Optional[str]
    effort: Optional[str]


@dataclass(frozen=True)
class DelegationConfig:
    strategy: str
    max_agents: int
    default_model: Optional[str]
    instructions: Optional[str]


@dataclass(frozen=True)
class AgentStep:
    id: str
    type: str
    model: Optional[str]
    mode: str
    prompt: str
    inputs: tuple[str, ...]
    output: Optional[str]
    delegation: DelegationConfig


@dataclass(frozen=True)
class ApprovalStep:
    id: str
    type: str
    message: str


@dataclass(frozen=True)
class ShellStep:
    id: str
    type: str
    command: tuple[str, ...]
    output: Optional[str]


@dataclass(frozen=True)
class ParallelStep:
    id: str
    type: str
    steps: tuple[AgentStep, ...]


WorkflowStep = Union[AgentStep, ApprovalStep, ShellStep, ParallelStep]


@dataclass(frozen=True)
class Workflow:
    version: int
    name: str
    models: dict[str, ModelProfile]
    default_model: Optional[str]
    steps: tuple[WorkflowStep, ...]

    def model_for(self, step: AgentStep) -> ModelProfile:
        profile_name = step.model or self.default_model
        if profile_name is None:
            raise WorkflowConfigError(f'Agent step {step.id!r} does not select a model profile')
        return self.models[profile_name]

    def delegated_model_for(self, step: AgentStep) -> Optional[ModelProfile]:
        profile_name = step.delegation.default_model
        if profile_name is None:
            return None
        return self.models[profile_name]


def load_workflow(path: Path) -> Workflow:
    source_path = path.resolve()
    if not source_path.is_file():
        raise WorkflowConfigError(f'Workflow does not exist: {source_path}')

    try:
        data = yaml.safe_load(source_path.read_text(encoding='utf-8'))
    except yaml.YAMLError as error:
        raise WorkflowConfigError(f'Invalid workflow YAML: {error}') from error

    return parse_workflow(data, source_path.parent)


def load_workflow_snapshot(path: Path) -> Workflow:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as error:
        raise WorkflowConfigError(f'Cannot read workflow snapshot {path}: {error}') from error

    return parse_workflow(data, path.parent)


def parse_workflow(data: object, source_directory: Path) -> Workflow:
    root = _require_mapping(data, 'workflow')
    version = root.get('version')
    if version != 1:
        raise WorkflowConfigError('Workflow version must be 1')

    name = _require_string(root.get('name'), 'workflow.name')
    models = _parse_models(root.get('models'))

    defaults = root.get('defaults', {})
    defaults_mapping = _require_mapping(defaults, 'workflow.defaults')
    default_model = _optional_string(defaults_mapping.get('model'), 'workflow.defaults.model')
    if default_model is not None and default_model not in models:
        raise WorkflowConfigError(f'Unknown default model profile: {default_model}')

    raw_steps = _require_list(root.get('steps'), 'workflow.steps')
    if not raw_steps:
        raise WorkflowConfigError('Workflow must contain at least one step')

    steps = tuple(_parse_step(raw_step, source_directory) for raw_step in raw_steps)
    workflow = Workflow(version=version, name=name, models=models, default_model=default_model, steps=steps)
    _validate_workflow(workflow)
    return workflow


def workflow_snapshot(workflow: Workflow) -> dict:
    return {
        'version': workflow.version,
        'name': workflow.name,
        'models': {
            name: {
                'provider': profile.provider,
                'model': profile.model,
                'effort': profile.effort,
            }
            for name, profile in workflow.models.items()
        },
        'defaults': {'model': workflow.default_model},
        'steps': [_step_snapshot(step) for step in workflow.steps],
    }


def _parse_models(value: object) -> dict[str, ModelProfile]:
    raw_models = _require_mapping(value, 'workflow.models')
    if not raw_models:
        raise WorkflowConfigError('Workflow must define at least one model profile')

    models = {}
    for name, raw_profile in raw_models.items():
        profile_name = _require_string(name, 'model profile name')
        profile = _require_mapping(raw_profile, f'models.{profile_name}')
        provider = _require_string(profile.get('provider'), f'models.{profile_name}.provider')
        if provider not in SUPPORTED_PROVIDERS:
            raise WorkflowConfigError(f'Unsupported provider for model profile {profile_name!r}: {provider}')

        models[profile_name] = ModelProfile(
            name=profile_name,
            provider=provider,
            model=_optional_string(profile.get('model'), f'models.{profile_name}.model'),
            effort=_optional_string(profile.get('effort'), f'models.{profile_name}.effort'),
        )
    return models


def _parse_step(value: object, source_directory: Path) -> WorkflowStep:
    raw_step = _require_mapping(value, 'workflow step')
    step_id = _require_identifier(raw_step.get('id'), 'step.id')
    step_type = _require_string(raw_step.get('type'), f'step {step_id}.type')
    if step_type not in SUPPORTED_STEP_TYPES:
        raise WorkflowConfigError(f'Unsupported step type for {step_id!r}: {step_type}')

    if step_type == 'agent':
        return _parse_agent_step(raw_step, source_directory, step_id)
    if step_type == 'approval':
        return ApprovalStep(
            id=step_id,
            type=step_type,
            message=_require_string(raw_step.get('message'), f'step {step_id}.message'),
        )
    if step_type == 'shell':
        command = _require_string_list(raw_step.get('command'), f'step {step_id}.command')
        if not command:
            raise WorkflowConfigError(f'Shell step {step_id!r} must contain a command')
        return ShellStep(
            id=step_id,
            type=step_type,
            command=tuple(command),
            output=_optional_relative_path(raw_step.get('output'), f'step {step_id}.output'),
        )

    raw_children = _require_list(raw_step.get('steps'), f'step {step_id}.steps')
    if not raw_children:
        raise WorkflowConfigError(f'Parallel step {step_id!r} must contain at least one child')

    children = []
    for raw_child in raw_children:
        child = _parse_step(raw_child, source_directory)
        if not isinstance(child, AgentStep):
            raise WorkflowConfigError(f'Parallel step {step_id!r} may contain only agent steps')
        if child.mode != 'read':
            raise WorkflowConfigError(f'Parallel child {child.id!r} must use read mode')
        children.append(child)
    return ParallelStep(id=step_id, type=step_type, steps=tuple(children))


def _parse_agent_step(raw_step: dict, source_directory: Path, step_id: str) -> AgentStep:
    mode = raw_step.get('mode', 'read')
    if mode not in SUPPORTED_MODES:
        raise WorkflowConfigError(f'Unsupported mode for agent step {step_id!r}: {mode}')

    prompt = _parse_prompt(raw_step, source_directory, step_id)
    inputs = _require_string_list(raw_step.get('inputs', []), f'step {step_id}.inputs')
    for input_path in inputs:
        _validate_relative_path(input_path, f'step {step_id}.inputs')

    return AgentStep(
        id=step_id,
        type='agent',
        model=_optional_string(raw_step.get('model'), f'step {step_id}.model'),
        mode=mode,
        prompt=prompt,
        inputs=tuple(inputs),
        output=_optional_relative_path(raw_step.get('output'), f'step {step_id}.output'),
        delegation=_parse_delegation(raw_step.get('delegation', {}), step_id),
    )


def _parse_prompt(raw_step: dict, source_directory: Path, step_id: str) -> str:
    prompt = raw_step.get('prompt')
    prompt_file = raw_step.get('prompt_file')
    if (prompt is None) == (prompt_file is None):
        raise WorkflowConfigError(f'Agent step {step_id!r} must define exactly one of prompt or prompt_file')

    if prompt is not None:
        return _require_string(prompt, f'step {step_id}.prompt')

    relative_path = _require_relative_path(prompt_file, f'step {step_id}.prompt_file')
    resolved_path = _resolve_source_file(source_directory, relative_path, f'step {step_id}.prompt_file')
    return resolved_path.read_text(encoding='utf-8')


def _parse_delegation(value: object, step_id: str) -> DelegationConfig:
    raw_delegation = _require_mapping(value, f'step {step_id}.delegation')
    strategy = raw_delegation.get('strategy', 'off')
    if strategy not in SUPPORTED_DELEGATION_STRATEGIES:
        raise WorkflowConfigError(f'Unsupported delegation strategy for {step_id!r}: {strategy}')

    default_max_agents = 2 if strategy == 'native' else 0
    max_agents = raw_delegation.get('max_agents', default_max_agents)
    if not isinstance(max_agents, int) or isinstance(max_agents, bool):
        raise WorkflowConfigError(f'step {step_id}.delegation.max_agents must be an integer')
    if strategy == 'native' and not 1 <= max_agents <= 8:
        raise WorkflowConfigError(f'step {step_id}.delegation.max_agents must be between 1 and 8')
    if strategy == 'off' and max_agents != 0:
        raise WorkflowConfigError(f'step {step_id}.delegation.max_agents must be 0 when delegation is off')

    return DelegationConfig(
        strategy=strategy,
        max_agents=max_agents,
        default_model=_optional_string(
            raw_delegation.get('default_model'),
            f'step {step_id}.delegation.default_model',
        ),
        instructions=_optional_string(raw_delegation.get('instructions'), f'step {step_id}.delegation.instructions'),
    )


def _validate_workflow(workflow: Workflow) -> None:
    step_ids = set()
    output_paths = set()
    for step in workflow.steps:
        _register_step_id(step.id, step_ids)
        if isinstance(step, ParallelStep):
            for child in step.steps:
                _register_step_id(child.id, step_ids)
                _validate_agent_step(workflow, child)
                _register_output(child.output, output_paths, child.id)
        elif isinstance(step, AgentStep):
            _validate_agent_step(workflow, step)
            _register_output(step.output, output_paths, step.id)
        elif isinstance(step, ShellStep):
            _register_output(step.output, output_paths, step.id)


def _validate_agent_step(workflow: Workflow, step: AgentStep) -> None:
    if step.model is not None and step.model not in workflow.models:
        raise WorkflowConfigError(f'Unknown model profile for step {step.id!r}: {step.model}')
    if step.delegation.default_model is not None and step.delegation.default_model not in workflow.models:
        raise WorkflowConfigError(
            f'Unknown delegated model profile for step {step.id!r}: {step.delegation.default_model}'
        )

    profile = workflow.model_for(step)
    delegation_profile = workflow.delegated_model_for(step)
    if delegation_profile is not None and step.delegation.strategy != 'native':
        raise WorkflowConfigError(f'Step {step.id!r} selects a delegated model while delegation is off')
    if delegation_profile is not None and delegation_profile.provider != profile.provider:
        raise WorkflowConfigError(f'Native delegation for step {step.id!r} cannot cross providers')


def _register_step_id(step_id: str, step_ids: set[str]) -> None:
    if step_id in step_ids:
        raise WorkflowConfigError(f'Duplicate step id: {step_id}')
    step_ids.add(step_id)


def _register_output(output: Optional[str], output_paths: set[str], step_id: str) -> None:
    if output is None:
        return
    if output in output_paths:
        raise WorkflowConfigError(f'Duplicate output path {output!r} on step {step_id!r}')
    output_paths.add(output)


def _step_snapshot(step: WorkflowStep) -> dict:
    if isinstance(step, AgentStep):
        return {
            'id': step.id,
            'type': step.type,
            'model': step.model,
            'mode': step.mode,
            'prompt': step.prompt,
            'inputs': list(step.inputs),
            'output': step.output,
            'delegation': {
                'strategy': step.delegation.strategy,
                'max_agents': step.delegation.max_agents,
                'default_model': step.delegation.default_model,
                'instructions': step.delegation.instructions,
            },
        }
    if isinstance(step, ApprovalStep):
        return {'id': step.id, 'type': step.type, 'message': step.message}
    if isinstance(step, ShellStep):
        return {'id': step.id, 'type': step.type, 'command': list(step.command), 'output': step.output}
    return {
        'id': step.id,
        'type': step.type,
        'steps': [_step_snapshot(child) for child in step.steps],
    }


def _resolve_source_file(source_directory: Path, relative_path: str, field_name: str) -> Path:
    resolved_path = (source_directory / relative_path).resolve()
    if not resolved_path.is_relative_to(source_directory.resolve()):
        raise WorkflowConfigError(f'{field_name} must stay inside the workflow directory')
    if not resolved_path.is_file():
        raise WorkflowConfigError(f'{field_name} does not exist: {resolved_path}')
    return resolved_path


def _require_mapping(value: object, field_name: str) -> dict:
    if not isinstance(value, dict):
        raise WorkflowConfigError(f'{field_name} must be a mapping')
    return value


def _require_list(value: object, field_name: str) -> list:
    if not isinstance(value, list):
        raise WorkflowConfigError(f'{field_name} must be a list')
    return value


def _require_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowConfigError(f'{field_name} must be a non-empty string')
    return value


def _optional_string(value: object, field_name: str) -> Optional[str]:
    if value is None:
        return None
    return _require_string(value, field_name)


def _require_string_list(value: object, field_name: str) -> list[str]:
    values = _require_list(value, field_name)
    return [_require_string(item, field_name) for item in values]


def _require_identifier(value: object, field_name: str) -> str:
    identifier = _require_string(value, field_name)
    has_invalid_character = any(not (character.isalnum() or character in {'-', '_'}) for character in identifier)
    if not identifier[0].isalnum() or has_invalid_character:
        raise WorkflowConfigError(f'{field_name} must contain only letters, numbers, hyphens, and underscores')
    return identifier


def _require_relative_path(value: object, field_name: str) -> str:
    relative_path = _require_string(value, field_name)
    _validate_relative_path(relative_path, field_name)
    return relative_path


def _optional_relative_path(value: object, field_name: str) -> Optional[str]:
    if value is None:
        return None
    return _require_relative_path(value, field_name)


def _validate_relative_path(value: str, field_name: str) -> None:
    path = PurePath(value)
    if path.is_absolute() or '..' in path.parts or value in {'', '.'}:
        raise WorkflowConfigError(f'{field_name} must be a safe relative path')
