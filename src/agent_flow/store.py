import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from agent_flow.config import ParallelStep, Workflow, workflow_snapshot

RUNS_DIRECTORY = Path('.agent-flow') / 'runs'


class RunStoreError(RuntimeError):
    pass


@dataclass
class RunState:
    run_id: str
    workflow_name: str
    repository_root: str
    status: str
    current_step: int
    waiting_step: Optional[str]
    waiting_message: Optional[str]
    created_at: str
    updated_at: str
    steps: dict[str, dict]

    def to_dict(self) -> dict:
        return {
            'run_id': self.run_id,
            'workflow_name': self.workflow_name,
            'repository_root': self.repository_root,
            'status': self.status,
            'current_step': self.current_step,
            'waiting_step': self.waiting_step,
            'waiting_message': self.waiting_message,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'steps': self.steps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'RunState':
        return cls(
            run_id=data['run_id'],
            workflow_name=data['workflow_name'],
            repository_root=data['repository_root'],
            status=data['status'],
            current_step=data['current_step'],
            waiting_step=data.get('waiting_step'),
            waiting_message=data.get('waiting_message'),
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            steps=data['steps'],
        )


class RunStore:
    def __init__(self, run_directory: Path):
        self.run_directory = run_directory.resolve()
        self.log_directory = self.run_directory / 'logs'
        self.state_path = self.run_directory / 'state.json'
        self.workflow_path = self.run_directory / 'workflow.json'
        self.events_path = self.run_directory / 'events.jsonl'

    @classmethod
    def create(cls, repository_root: Path, workflow: Workflow, request_path: Path) -> tuple['RunStore', RunState]:
        source_request = request_path.resolve()
        if not source_request.is_file():
            raise RunStoreError(f'Request file does not exist: {source_request}')
        return cls.create_from_text(repository_root, workflow, source_request.read_text(encoding='utf-8'))

    @classmethod
    def create_from_text(
        cls,
        repository_root: Path,
        workflow: Workflow,
        request_text: str,
    ) -> tuple['RunStore', RunState]:
        root = repository_root.resolve()
        if not root.is_dir():
            raise RunStoreError(f'Repository root does not exist: {root}')
        if not request_text.strip():
            raise RunStoreError('Request text must not be empty')

        now = _now()
        run_id = f'{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}-{_slug(workflow.name)}-{uuid.uuid4().hex[:8]}'
        store = cls(root / RUNS_DIRECTORY / run_id)
        store.log_directory.mkdir(parents=True)
        (store.run_directory / 'request.md').write_text(request_text.rstrip() + '\n', encoding='utf-8')
        store.workflow_path.write_text(json.dumps(workflow_snapshot(workflow), indent=2) + '\n', encoding='utf-8')

        step_records = {}
        for step in workflow.steps:
            step_records[step.id] = _new_step_record()
            if isinstance(step, ParallelStep):
                for child in step.steps:
                    step_records[child.id] = _new_step_record(parent=step.id)

        state = RunState(
            run_id=run_id,
            workflow_name=workflow.name,
            repository_root=str(root),
            status='ready',
            current_step=0,
            waiting_step=None,
            waiting_message=None,
            created_at=now,
            updated_at=now,
            steps=step_records,
        )
        store.save_state(state)
        store.append_event('run.created', {'workflow': workflow.name})
        return store, state

    @classmethod
    def open(cls, repository_root: Path, run_reference: str) -> 'RunStore':
        reference_path = Path(run_reference)
        if reference_path.name != run_reference or run_reference in {'.', '..'}:
            raise RunStoreError('Run reference must be a run ID, not a path')
        run_directory = repository_root.resolve() / RUNS_DIRECTORY / run_reference

        store = cls(run_directory)
        if not store.state_path.is_file() or not store.workflow_path.is_file():
            raise RunStoreError(f'Run does not exist or is incomplete: {store.run_directory}')
        return store

    def load_state(self) -> RunState:
        try:
            data = json.loads(self.state_path.read_text(encoding='utf-8'))
            return RunState.from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError) as error:
            raise RunStoreError(f'Cannot read run state {self.state_path}: {error}') from error

    def save_state(self, state: RunState) -> None:
        state.updated_at = _now()
        _atomic_json_write(self.state_path, state.to_dict())

    def append_event(self, event_type: str, data: dict) -> None:
        event = {'time': _now(), 'type': event_type, **data}
        with self.events_path.open('a', encoding='utf-8') as events_file:
            events_file.write(json.dumps(event, sort_keys=True) + '\n')

    def resolve_input(self, repository_root: Path, relative_path: str) -> Path:
        run_path = (self.run_directory / relative_path).resolve()
        if run_path.is_relative_to(self.run_directory) and run_path.is_file():
            return run_path

        repository_path = (repository_root / relative_path).resolve()
        if repository_path.is_relative_to(repository_root.resolve()) and repository_path.is_file():
            return repository_path
        raise RunStoreError(f'Input does not exist in the run or repository: {relative_path}')

    def write_artifact(self, relative_path: str, content: str) -> Path:
        destination = (self.run_directory / relative_path).resolve()
        if not destination.is_relative_to(self.run_directory):
            raise RunStoreError(f'Artifact path escapes the run directory: {relative_path}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content.rstrip() + '\n', encoding='utf-8')
        return destination


def _new_step_record(parent: Optional[str] = None) -> dict:
    return {
        'status': 'pending',
        'attempts': 0,
        'started_at': None,
        'completed_at': None,
        'error': None,
        'metadata': {},
        'parent': parent,
    }


def _atomic_json_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as temporary_file:
            json.dump(data, temporary_file, indent=2)
            temporary_file.write('\n')
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    slug = ''.join(character.lower() if character.isalnum() else '-' for character in value)
    return '-'.join(part for part in slug.split('-') if part) or 'workflow'
