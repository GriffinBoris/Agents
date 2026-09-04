import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from agent_flow.config import ParallelStep, Workflow, workflow_snapshot

try:
    import fcntl
except ImportError:  # pragma: no cover - only used on non-POSIX hosts
    fcntl = None

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
        self.lock_path = self.run_directory / '.lock'

    @property
    def repository_root(self) -> Path:
        return self.run_directory.parents[2]

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
        runs_directory = (root / RUNS_DIRECTORY).resolve()
        if not runs_directory.is_relative_to(root):
            raise RunStoreError(f'Runs directory resolves outside the repository: {runs_directory}')
        store = cls(runs_directory / run_id)
        store.log_directory.mkdir(parents=True)
        atomic_text_write(store.run_directory / 'request.md', request_text.rstrip() + '\n')
        atomic_text_write(store.workflow_path, json.dumps(workflow_snapshot(workflow), indent=2) + '\n')

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
        root = repository_root.resolve()
        runs_directory = (root / RUNS_DIRECTORY).resolve()
        if not runs_directory.is_relative_to(root):
            raise RunStoreError(f'Runs directory resolves outside the repository: {runs_directory}')
        run_directory = (runs_directory / run_reference).resolve()
        if not run_directory.is_relative_to(runs_directory):
            raise RunStoreError('Run reference resolves outside the runs directory')

        store = cls(run_directory)
        if (
            store.state_path.is_symlink()
            or store.workflow_path.is_symlink()
            or not store.state_path.is_file()
            or not store.workflow_path.is_file()
        ):
            raise RunStoreError(f'Run does not exist or is incomplete: {store.run_directory}')
        return store

    def load_state(self) -> RunState:
        try:
            data = json.loads(self.state_path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                raise ValueError('state must be a JSON object')
            state = RunState.from_dict(data)
            _validate_state(state)
            if state.run_id != self.run_directory.name:
                raise ValueError('run_id does not match its run directory')
            state.repository_root = str(self.repository_root)
            return state
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as error:
            raise RunStoreError(f'Cannot read run state {self.state_path}: {error}') from error

    def save_state(self, state: RunState) -> None:
        state.updated_at = _now()
        _atomic_json_write(self.state_path, state.to_dict())

    @contextmanager
    def lock(self):
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.lock_path, flags, 0o600)
        except OSError as error:
            raise RunStoreError(f'Cannot lock run {self.run_directory}: {error}') from error
        try:
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def append_event(self, event_type: str, data: dict) -> None:
        event = {'time': _now(), 'type': event_type, **data}
        encoded = (json.dumps(event, sort_keys=True) + '\n').encode('utf-8')
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.events_path, flags, 0o600)
            try:
                written = os.write(descriptor, encoded)
                if written != len(encoded):
                    raise OSError(f'wrote only {written} of {len(encoded)} event bytes')
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as error:
            raise RunStoreError(f'Cannot append run event {self.events_path}: {error}') from error

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
        atomic_text_write(destination, content.rstrip() + '\n')
        return destination

    def write_log(self, step_id: str, content: str) -> Path:
        destination = (self.log_directory / f'{step_id}.log').resolve()
        if not destination.is_relative_to(self.log_directory.resolve()):
            raise RunStoreError(f'Log path escapes the log directory: {step_id}')
        atomic_text_write(destination, content)
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


def _validate_state(state: RunState) -> None:
    if not all(isinstance(value, str) and value for value in (state.run_id, state.workflow_name)):
        raise ValueError('run_id and workflow_name must be non-empty strings')
    allowed_statuses = {'ready', 'running', 'failed', 'waiting_for_approval', 'completed'}
    if state.status not in allowed_statuses:
        raise ValueError(f'unsupported run status: {state.status!r}')
    if not isinstance(state.current_step, int) or isinstance(state.current_step, bool) or state.current_step < 0:
        raise ValueError('current_step must be a non-negative integer')
    if not isinstance(state.steps, dict):
        raise ValueError('steps must be a JSON object')
    step_statuses = {'pending', 'running', 'succeeded', 'failed', 'waiting'}
    for step_id, record in state.steps.items():
        if not isinstance(step_id, str) or not isinstance(record, dict):
            raise ValueError('each step record must be a named JSON object')
        if record.get('status') not in step_statuses:
            raise ValueError(f'unsupported status for step {step_id!r}')
        attempts = record.get('attempts')
        if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 0:
            raise ValueError(f'invalid attempts for step {step_id!r}')
        if not isinstance(record.get('metadata'), dict):
            raise ValueError(f'invalid metadata for step {step_id!r}')


def _atomic_json_write(path: Path, data: dict) -> None:
    atomic_text_write(path, json.dumps(data, indent=2) + '\n')


def atomic_text_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_name, path)
        try:
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_descriptor = None
        if directory_descriptor is not None:
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
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
