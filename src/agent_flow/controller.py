import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from agent_flow.config import (
    AgentStep,
    ApprovalStep,
    ParallelStep,
    ShellStep,
    Workflow,
    WorkflowStep,
    load_workflow_snapshot,
)
from agent_flow.store import RunState, RunStore


class WorkflowStateError(RuntimeError):
    pass


class WorkflowController:
    """Maintain durable workflow state without launching agent providers."""

    def start(self, workflow: Workflow, request_path: Path, repository_root: Path) -> tuple[RunStore, RunState]:
        store, state = RunStore.create(repository_root, workflow, request_path)
        self._set_boundary(workflow, store, state)
        return store, state

    def start_text(self, workflow: Workflow, request_text: str, repository_root: Path) -> tuple[RunStore, RunState]:
        store, state = RunStore.create_from_text(repository_root, workflow, request_text)
        self._set_boundary(workflow, store, state)
        return store, state

    def begin(self, store: RunStore, step_id: str, *, allow_shell: bool = False) -> RunState:
        workflow = load_workflow_snapshot(store.workflow_path)
        state = store.load_state()
        step = self._current_step(workflow, state)
        self._require_step(step, step_id)
        if isinstance(step, ApprovalStep):
            raise WorkflowStateError(f'Step {step.id!r} requires approval, not begin')
        if isinstance(step, ShellStep) and not allow_shell:
            raise WorkflowStateError(f'Step {step.id!r} must be executed with the shell command')
        if state.status not in {'ready', 'failed'}:
            raise WorkflowStateError(f'Run cannot begin a step from status {state.status!r}')

        self._mark_started(state.steps[step.id])
        if isinstance(step, AgentStep):
            self._record_artifact_baseline(store, step, state.steps[step.id])
        if isinstance(step, ParallelStep):
            for child in step.steps:
                self._mark_started(state.steps[child.id])
                self._record_artifact_baseline(store, child, state.steps[child.id])
        state.status = 'running'
        store.save_state(state)
        store.append_event('step.started', {'step': step.id, 'step_type': step.type})
        return state

    def attach_worker(
        self,
        store: RunStore,
        step_id: str,
        worker_id: str,
        *,
        parent_worker_id: str | None = None,
    ) -> RunState:
        with store.lock():
            return self._attach_worker(store, step_id, worker_id, parent_worker_id=parent_worker_id)

    def _attach_worker(
        self,
        store: RunStore,
        step_id: str,
        worker_id: str,
        *,
        parent_worker_id: str | None = None,
    ) -> RunState:
        if not worker_id.strip():
            raise WorkflowStateError('Worker ID must not be empty')
        if parent_worker_id is not None and not parent_worker_id.strip():
            raise WorkflowStateError('Parent worker ID must not be empty')
        if parent_worker_id == worker_id:
            raise WorkflowStateError('A worker cannot be its own parent')
        workflow = load_workflow_snapshot(store.workflow_path)
        state = store.load_state()
        if state.status != 'running':
            raise WorkflowStateError('Workers can be attached only while a step is running')
        record = state.steps.get(step_id)
        if record is None or record['status'] != 'running':
            raise WorkflowStateError(f'Step {step_id!r} is not a running workflow step')

        step = self._running_agent_step(workflow, state, step_id)

        worker_ids = record['metadata'].setdefault('worker_ids', [])
        workers = record['metadata'].setdefault('workers', [])
        if not isinstance(worker_ids, list) or not all(isinstance(value, str) for value in worker_ids):
            raise WorkflowStateError(f'Step {step_id!r} contains invalid worker IDs')
        if not isinstance(workers, list) or not all(isinstance(value, dict) for value in workers):
            raise WorkflowStateError(f'Step {step_id!r} contains invalid worker details')
        if parent_worker_id is not None and parent_worker_id not in worker_ids:
            raise WorkflowStateError(f'Parent worker {parent_worker_id!r} is not attached to step {step_id!r}')
        existing = next((worker for worker in workers if worker.get('id') == worker_id), None)
        if existing is not None:
            if existing.get('parent_worker_id') != parent_worker_id:
                raise WorkflowStateError(f'Worker {worker_id!r} is already attached with a different parent')
            return state
        if parent_worker_id is not None and step.delegation.strategy != 'native':
            raise WorkflowStateError(f'Step {step_id!r} does not allow nested workers')
        if parent_worker_id is not None:
            nested_count = sum(worker.get('parent_worker_id') == parent_worker_id for worker in workers)
            if nested_count >= step.delegation.max_agents:
                raise WorkflowStateError(
                    f'Parent worker {parent_worker_id!r} already has the maximum of '
                    f'{step.delegation.max_agents} nested workers'
                )
        profile = workflow.delegated_model_for(step) if parent_worker_id is not None else workflow.model_for(step)
        if profile is None:
            profile = workflow.model_for(step)
        if worker_id not in worker_ids:
            worker_ids.append(worker_id)
        worker = {
            'id': worker_id,
            'parent_worker_id': parent_worker_id,
            'attempt': record['attempts'],
            'model': {
                'profile': profile.name,
                'provider': profile.provider,
                'model': profile.model,
                'effort': profile.effort,
            },
        }
        workers.append(worker)
        store.save_state(state)
        store.append_event(
            'worker.attached',
            {
                'step': step_id,
                'worker_id': worker_id,
                'parent_worker_id': parent_worker_id,
                'model_profile': profile.name,
            },
        )
        return state

    def complete(self, store: RunStore, step_id: str, *, allow_shell: bool = False) -> RunState:
        workflow = load_workflow_snapshot(store.workflow_path)
        state = store.load_state()
        step = self._current_step(workflow, state)
        self._require_step(step, step_id)
        if isinstance(step, ApprovalStep):
            raise WorkflowStateError(f'Step {step.id!r} requires approval, not completion')
        if isinstance(step, ShellStep) and not allow_shell:
            raise WorkflowStateError(f'Step {step.id!r} must be executed with the shell command')
        if state.status != 'running':
            raise WorkflowStateError(f'Run cannot complete a step from status {state.status!r}')

        if isinstance(step, AgentStep):
            artifact = self._require_agent_artifact(store, step, state.steps[step.id])
            state.steps[step.id]['metadata']['artifact'] = str(artifact)
            state.steps[step.id]['metadata'].pop('_artifact_baseline', None)
        elif isinstance(step, ParallelStep):
            artifacts = {}
            for child in step.steps:
                artifact = self._require_agent_artifact(store, child, state.steps[child.id])
                artifacts[child.id] = str(artifact)
                child_record = state.steps[child.id]
                child_record['status'] = 'succeeded'
                child_record['completed_at'] = _now()
                child_record['error'] = None
                child_record['metadata']['artifact'] = str(artifact)
                child_record['metadata'].pop('_artifact_baseline', None)
            state.steps[step.id]['metadata']['artifacts'] = artifacts

        record = state.steps[step.id]
        record['status'] = 'succeeded'
        record['completed_at'] = _now()
        record['error'] = None
        state.current_step += 1
        self._set_boundary(
            workflow,
            store,
            state,
            preceding_event=('step.succeeded', {'step': step.id, 'metadata': record['metadata']}),
        )
        return state

    def fail(self, store: RunStore, step_id: str, message: str) -> RunState:
        if not message.strip():
            raise WorkflowStateError('Failure message must not be empty')
        workflow = load_workflow_snapshot(store.workflow_path)
        state = store.load_state()
        step = self._current_step(workflow, state)
        self._require_step(step, step_id)
        if state.status != 'running':
            raise WorkflowStateError(f'Run cannot fail a step from status {state.status!r}')

        record = state.steps[step.id]
        record['status'] = 'failed'
        record['completed_at'] = _now()
        record['error'] = message
        if isinstance(step, ParallelStep):
            for child in step.steps:
                child_record = state.steps[child.id]
                if child_record['status'] == 'running':
                    child_record['status'] = 'failed'
                    child_record['completed_at'] = _now()
                    child_record['error'] = message
        state.status = 'failed'
        store.save_state(state)
        store.append_event('step.failed', {'step': step.id, 'error': message})
        return state

    def approve(self, store: RunStore) -> RunState:
        workflow = load_workflow_snapshot(store.workflow_path)
        state = store.load_state()
        step = self._current_step(workflow, state)
        if not isinstance(step, ApprovalStep):
            raise WorkflowStateError('The current workflow step is not an approval')
        if state.status != 'waiting_for_approval' or state.waiting_step != step.id:
            raise WorkflowStateError('Run is not waiting for approval')

        record = state.steps[step.id]
        record['status'] = 'succeeded'
        record['completed_at'] = _now()
        record['error'] = None
        state.current_step += 1
        state.waiting_step = None
        state.waiting_message = None
        self._set_boundary(
            workflow,
            store,
            state,
            preceding_event=('step.approved', {'step': step.id}),
        )
        return state

    def run_shell(self, store: RunStore, step_id: str) -> RunState:
        workflow = load_workflow_snapshot(store.workflow_path)
        state = store.load_state()
        step = self._current_step(workflow, state)
        self._require_step(step, step_id)
        if not isinstance(step, ShellStep):
            raise WorkflowStateError(f'Step {step.id!r} is not a shell step')

        self.begin(store, step_id, allow_shell=True)
        try:
            completed_process = subprocess.run(
                list(step.command),
                cwd=store.repository_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=False,
                timeout=step.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            log_path = store.write_log(
                step.id,
                _shell_log(step.command, _subprocess_text(error.stdout), _subprocess_text(error.stderr)),
            )
            message = f'Command timed out after {step.timeout_seconds} seconds; see {log_path}'
            self.fail(store, step.id, message)
            raise WorkflowStateError(message) from error
        except KeyboardInterrupt as error:
            log_path = store.write_log(step.id, _shell_log(step.command, '', 'Interrupted by user'))
            message = f'Command was interrupted; see {log_path}'
            self.fail(store, step.id, message)
            raise WorkflowStateError(message) from error
        except OSError as error:
            log_path = store.write_log(step.id, _shell_log(step.command, '', str(error)))
            message = f'Cannot execute command: {error}; see {log_path}'
            self.fail(store, step.id, message)
            raise WorkflowStateError(message) from error

        log_path = store.write_log(
            step.id,
            _shell_log(step.command, completed_process.stdout, completed_process.stderr),
        )
        if step.output is not None:
            store.write_artifact(step.output, completed_process.stdout)
        if completed_process.returncode != 0:
            message = f'Command exited with code {completed_process.returncode}; see {log_path}'
            self.fail(store, step.id, message)
            raise WorkflowStateError(message)

        state = store.load_state()
        state.steps[step.id]['metadata'].update(
            {'command': list(step.command), 'returncode': completed_process.returncode, 'log': str(log_path)}
        )
        store.save_state(state)
        return self.complete(store, step.id, allow_shell=True)

    def describe(self, workflow: Workflow, store: RunStore, state: RunState) -> dict:
        step = None
        if state.current_step < len(workflow.steps):
            step = self._describe_step(workflow, workflow.steps[state.current_step], store, store.repository_root)
        return {
            'run_id': state.run_id,
            'run_directory': str(store.run_directory),
            'status': state.status,
            'current_step': state.current_step,
            'waiting_step': state.waiting_step,
            'waiting_message': state.waiting_message,
            'step': step,
        }

    def _set_boundary(
        self,
        workflow: Workflow,
        store: RunStore,
        state: RunState,
        *,
        preceding_event: tuple[str, dict] | None = None,
    ) -> None:
        boundary_event = None
        if state.current_step >= len(workflow.steps):
            state.status = 'completed'
            state.waiting_step = None
            state.waiting_message = None
            boundary_event = ('run.completed', {'workflow': workflow.name})
        elif isinstance(workflow.steps[state.current_step], ApprovalStep):
            step = workflow.steps[state.current_step]
            record = state.steps[step.id]
            record['status'] = 'waiting'
            record['started_at'] = record['started_at'] or _now()
            record['attempts'] = max(record['attempts'], 1)
            state.status = 'waiting_for_approval'
            state.waiting_step = step.id
            state.waiting_message = step.message
            boundary_event = ('step.waiting_for_approval', {'step': step.id, 'message': step.message})
        else:
            state.status = 'ready'
            state.waiting_step = None
            state.waiting_message = None
        store.save_state(state)
        if preceding_event is not None:
            store.append_event(*preceding_event)
        if boundary_event is not None:
            store.append_event(*boundary_event)

    @staticmethod
    def _current_step(workflow: Workflow, state: RunState) -> WorkflowStep:
        if state.current_step >= len(workflow.steps):
            raise WorkflowStateError('Workflow is already completed')
        return workflow.steps[state.current_step]

    @staticmethod
    def _require_step(step: WorkflowStep, step_id: str) -> None:
        if step.id != step_id:
            raise WorkflowStateError(f'Current step is {step.id!r}, not {step_id!r}')

    @classmethod
    def _running_agent_step(cls, workflow: Workflow, state: RunState, step_id: str) -> AgentStep:
        step = cls._current_step(workflow, state)
        if isinstance(step, AgentStep) and step.id == step_id:
            return step
        if isinstance(step, ParallelStep):
            child = next((child for child in step.steps if child.id == step_id), None)
            if child is not None:
                return child
        raise WorkflowStateError(f'Step {step_id!r} is not a running agent step')

    @staticmethod
    def _mark_started(record: dict) -> None:
        record['status'] = 'running'
        record['attempts'] += 1
        record['started_at'] = _now()
        record['completed_at'] = None
        record['error'] = None

    @staticmethod
    def _require_agent_artifact(store: RunStore, step: AgentStep, record: dict) -> Path:
        output_path = _agent_output(step)
        artifact = (store.run_directory / output_path).resolve()
        if not artifact.is_relative_to(store.run_directory) or not artifact.is_file():
            raise WorkflowStateError(f'Step {step.id!r} has no artifact at {artifact}')
        baseline = record.get('metadata', {}).get('_artifact_baseline')
        stat = artifact.stat()
        fingerprint = {'size': stat.st_size, 'modified_ns': stat.st_mtime_ns}
        if baseline == fingerprint:
            raise WorkflowStateError(f'Step {step.id!r} artifact predates the current attempt: {artifact}')
        return artifact

    @staticmethod
    def _record_artifact_baseline(store: RunStore, step: AgentStep, record: dict) -> None:
        artifact = (store.run_directory / _agent_output(step)).resolve()
        baseline = None
        if artifact.is_relative_to(store.run_directory) and artifact.is_file():
            stat = artifact.stat()
            baseline = {'size': stat.st_size, 'modified_ns': stat.st_mtime_ns}
        record['metadata']['_artifact_baseline'] = baseline

    def _describe_step(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        store: RunStore,
        repository_root: Path,
    ) -> dict:
        if isinstance(step, ApprovalStep):
            return {'id': step.id, 'type': step.type, 'message': step.message}
        if isinstance(step, ShellStep):
            return {
                'id': step.id,
                'type': step.type,
                'command': list(step.command),
                'output': str(store.run_directory / step.output) if step.output is not None else None,
                'timeout_seconds': step.timeout_seconds,
            }
        if isinstance(step, ParallelStep):
            return {
                'id': step.id,
                'type': step.type,
                'steps': [self._describe_agent(workflow, child, store, repository_root) for child in step.steps],
            }
        return self._describe_agent(workflow, step, store, repository_root)

    @staticmethod
    def _describe_agent(
        workflow: Workflow,
        step: AgentStep,
        store: RunStore,
        repository_root: Path,
    ) -> dict:
        profile = workflow.model_for(step)
        delegated_profile = workflow.delegated_model_for(step)
        inputs = [
            {'name': input_path, 'path': str(store.resolve_input(repository_root, input_path))}
            for input_path in step.inputs
        ]
        delegation = {
            'strategy': step.delegation.strategy,
            'max_agents': step.delegation.max_agents,
            'instructions': step.delegation.instructions,
            'model': None,
        }
        if delegated_profile is not None:
            delegation['model'] = {
                'profile': delegated_profile.name,
                'provider': delegated_profile.provider,
                'model': delegated_profile.model,
                'effort': delegated_profile.effort,
            }
        return {
            'id': step.id,
            'type': step.type,
            'mode': step.mode,
            'prompt': step.prompt,
            'inputs': inputs,
            'output': str(store.run_directory / _agent_output(step)),
            'model': {
                'profile': profile.name,
                'provider': profile.provider,
                'model': profile.model,
                'effort': profile.effort,
            },
            'delegation': delegation,
        }


def _agent_output(step: AgentStep) -> str:
    return step.output or f'artifacts/{step.id}.md'


def _shell_log(command: tuple[str, ...], stdout: str, stderr: str) -> str:
    return f'$ {shlex.join(command)}\n\nSTDOUT\n{stdout}\nSTDERR\n{stderr}'


def _subprocess_text(value: str | bytes | None) -> str:
    if value is None:
        return ''
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
