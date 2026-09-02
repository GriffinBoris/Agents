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
        if isinstance(step, ParallelStep):
            for child in step.steps:
                self._mark_started(state.steps[child.id])
        state.status = 'running'
        store.save_state(state)
        store.append_event('step.started', {'step': step.id, 'step_type': step.type})
        return state

    def attach_worker(self, store: RunStore, step_id: str, worker_id: str) -> RunState:
        state = store.load_state()
        if state.status != 'running':
            raise WorkflowStateError('Workers can be attached only while a step is running')
        record = state.steps.get(step_id)
        if record is None or record['status'] != 'running':
            raise WorkflowStateError(f'Step {step_id!r} is not a running workflow step')

        worker_ids = record['metadata'].setdefault('worker_ids', [])
        if worker_id not in worker_ids:
            worker_ids.append(worker_id)
        store.save_state(state)
        store.append_event('worker.attached', {'step': step_id, 'worker_id': worker_id})
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
            artifact = self._require_agent_artifact(store, step)
            state.steps[step.id]['metadata']['artifact'] = str(artifact)
        elif isinstance(step, ParallelStep):
            artifacts = {}
            for child in step.steps:
                artifact = self._require_agent_artifact(store, child)
                artifacts[child.id] = str(artifact)
                child_record = state.steps[child.id]
                child_record['status'] = 'succeeded'
                child_record['completed_at'] = _now()
                child_record['error'] = None
                child_record['metadata']['artifact'] = str(artifact)
            state.steps[step.id]['metadata']['artifacts'] = artifacts

        record = state.steps[step.id]
        record['status'] = 'succeeded'
        record['completed_at'] = _now()
        record['error'] = None
        state.current_step += 1
        store.append_event('step.succeeded', {'step': step.id, 'metadata': record['metadata']})
        self._set_boundary(workflow, store, state)
        return state

    def fail(self, store: RunStore, step_id: str, message: str) -> RunState:
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
        store.append_event('step.approved', {'step': step.id})
        self._set_boundary(workflow, store, state)
        return state

    def run_shell(self, store: RunStore, step_id: str) -> RunState:
        workflow = load_workflow_snapshot(store.workflow_path)
        state = store.load_state()
        step = self._current_step(workflow, state)
        self._require_step(step, step_id)
        if not isinstance(step, ShellStep):
            raise WorkflowStateError(f'Step {step.id!r} is not a shell step')

        self.begin(store, step_id, allow_shell=True)
        completed_process = subprocess.run(
            list(step.command),
            cwd=Path(state.repository_root),
            capture_output=True,
            text=True,
            check=False,
        )
        log_path = store.log_directory / f'{step.id}.log'
        log_path.write_text(
            f'$ {" ".join(step.command)}\n\nSTDOUT\n{completed_process.stdout}\nSTDERR\n{completed_process.stderr}',
            encoding='utf-8',
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
            step = self._describe_step(workflow, workflow.steps[state.current_step], store, Path(state.repository_root))
        return {
            'run_id': state.run_id,
            'run_directory': str(store.run_directory),
            'status': state.status,
            'current_step': state.current_step,
            'waiting_step': state.waiting_step,
            'waiting_message': state.waiting_message,
            'step': step,
        }

    def _set_boundary(self, workflow: Workflow, store: RunStore, state: RunState) -> None:
        if state.current_step >= len(workflow.steps):
            state.status = 'completed'
            state.waiting_step = None
            state.waiting_message = None
            store.save_state(state)
            store.append_event('run.completed', {'workflow': workflow.name})
            return

        step = workflow.steps[state.current_step]
        if isinstance(step, ApprovalStep):
            record = state.steps[step.id]
            record['status'] = 'waiting'
            record['started_at'] = record['started_at'] or _now()
            record['attempts'] = max(record['attempts'], 1)
            state.status = 'waiting_for_approval'
            state.waiting_step = step.id
            state.waiting_message = step.message
            store.save_state(state)
            store.append_event('step.waiting_for_approval', {'step': step.id, 'message': step.message})
            return

        state.status = 'ready'
        state.waiting_step = None
        state.waiting_message = None
        store.save_state(state)

    @staticmethod
    def _current_step(workflow: Workflow, state: RunState) -> WorkflowStep:
        if state.current_step >= len(workflow.steps):
            raise WorkflowStateError('Workflow is already completed')
        return workflow.steps[state.current_step]

    @staticmethod
    def _require_step(step: WorkflowStep, step_id: str) -> None:
        if step.id != step_id:
            raise WorkflowStateError(f'Current step is {step.id!r}, not {step_id!r}')

    @staticmethod
    def _mark_started(record: dict) -> None:
        record['status'] = 'running'
        record['attempts'] += 1
        record['started_at'] = _now()
        record['completed_at'] = None
        record['error'] = None

    @staticmethod
    def _require_agent_artifact(store: RunStore, step: AgentStep) -> Path:
        output_path = _agent_output(step)
        artifact = (store.run_directory / output_path).resolve()
        if not artifact.is_relative_to(store.run_directory) or not artifact.is_file():
            raise WorkflowStateError(f'Step {step.id!r} has no artifact at {artifact}')
        return artifact

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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
