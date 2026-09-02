import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jsonschema import SchemaError, ValidationError, validate

from agent_flow.adapters import AgentAdapter, AgentResult, default_adapters
from agent_flow.config import (
    AgentStep,
    ApprovalStep,
    ParallelStep,
    ShellStep,
    Workflow,
    load_workflow_snapshot,
)
from agent_flow.store import RunState, RunStore


class WorkflowExecutionError(RuntimeError):
    pass


class WorkflowRunner:
    def __init__(self, adapters: Optional[dict[str, AgentAdapter]] = None):
        self.adapters = adapters if adapters is not None else default_adapters()

    def start(self, workflow: Workflow, request_path: Path, repository_root: Path) -> tuple[RunStore, RunState]:
        store, state = RunStore.create(repository_root, workflow, request_path)
        return store, self._run(workflow, store, state)

    def resume(self, store: RunStore) -> RunState:
        workflow = load_workflow_snapshot(store.workflow_path)
        state = store.load_state()
        if state.status == 'waiting_for_approval':
            raise WorkflowExecutionError(
                f'Run is waiting for approval at {state.waiting_step!r}; approve it before resuming'
            )
        if state.status == 'completed':
            return state
        if state.status not in {'approved', 'failed', 'ready'}:
            raise WorkflowExecutionError(f'Run cannot resume from status {state.status!r}')
        return self._run(workflow, store, state)

    def approve(self, store: RunStore) -> RunState:
        workflow = load_workflow_snapshot(store.workflow_path)
        state = store.load_state()
        if state.status != 'waiting_for_approval' or state.waiting_step is None:
            raise WorkflowExecutionError('Run is not waiting for approval')

        step = workflow.steps[state.current_step]
        if not isinstance(step, ApprovalStep) or step.id != state.waiting_step:
            raise WorkflowExecutionError('Run approval state does not match the workflow snapshot')

        record = state.steps[step.id]
        record['status'] = 'succeeded'
        record['completed_at'] = _now()
        state.current_step += 1
        state.waiting_step = None
        state.waiting_message = None
        state.status = 'approved'
        store.save_state(state)
        store.append_event('step.approved', {'step': step.id})
        return state

    def _run(self, workflow: Workflow, store: RunStore, state: RunState) -> RunState:
        repository_root = Path(state.repository_root)
        state.status = 'running'
        store.save_state(state)

        while state.current_step < len(workflow.steps):
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
                return state

            self._mark_step_started(state, step.id)
            store.save_state(state)
            store.append_event('step.started', {'step': step.id, 'step_type': step.type})

            try:
                metadata = self._execute_step(workflow, step, store, repository_root, state)
            except KeyboardInterrupt:
                record = state.steps[step.id]
                record['status'] = 'failed'
                record['completed_at'] = _now()
                record['error'] = 'Interrupted by user'
                state.status = 'failed'
                store.save_state(state)
                store.append_event('step.interrupted', {'step': step.id})
                raise
            except Exception as error:
                record = state.steps[step.id]
                record['status'] = 'failed'
                record['completed_at'] = _now()
                record['error'] = str(error)
                state.status = 'failed'
                store.save_state(state)
                store.append_event('step.failed', {'step': step.id, 'error': str(error)})
                raise WorkflowExecutionError(f'Step {step.id!r} failed: {error}') from error

            record = state.steps[step.id]
            record['status'] = 'succeeded'
            record['completed_at'] = _now()
            record['error'] = None
            record['metadata'] = metadata
            state.current_step += 1
            store.save_state(state)
            store.append_event('step.succeeded', {'step': step.id, 'metadata': metadata})

        state.status = 'completed'
        store.save_state(state)
        store.append_event('run.completed', {'workflow': workflow.name})
        return state

    def _execute_step(
        self,
        workflow: Workflow,
        step: object,
        store: RunStore,
        repository_root: Path,
        state: RunState,
    ) -> dict:
        if isinstance(step, AgentStep):
            result = self._execute_agent(workflow, step, store, repository_root)
            return result.metadata
        if isinstance(step, ShellStep):
            return self._execute_shell(step, store, repository_root)
        if isinstance(step, ParallelStep):
            return self._execute_parallel(workflow, step, store, repository_root, state)
        raise WorkflowExecutionError(f'Unsupported executable step: {step}')

    def _execute_agent(
        self,
        workflow: Workflow,
        step: AgentStep,
        store: RunStore,
        repository_root: Path,
    ) -> AgentResult:
        profile = workflow.model_for(step)
        delegated_profile = workflow.delegated_model_for(step)
        adapter = self.adapters.get(profile.provider)
        if adapter is None:
            raise WorkflowExecutionError(f'No adapter is registered for provider {profile.provider!r}')

        prompt = self._render_prompt(step, store, repository_root)
        result = adapter.run(
            profile=profile,
            delegated_profile=delegated_profile,
            step=step,
            prompt=prompt,
            repository_root=repository_root,
            log_directory=store.log_directory,
        )
        output_text = self._validated_output(step, result.text)
        output_path = step.output or f'artifacts/{step.id}.{"json" if step.schema is not None else "md"}'
        store.write_artifact(output_path, output_text)
        metadata = {
            **result.metadata,
            'provider': profile.provider,
            'model_profile': profile.name,
            'model': profile.model,
            'effort': profile.effort,
            'delegation': step.delegation.strategy,
        }
        return AgentResult(text=output_text, metadata=metadata)

    def _execute_shell(self, step: ShellStep, store: RunStore, repository_root: Path) -> dict:
        completed_process = subprocess.run(
            list(step.command),
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
        )
        log_path = store.log_directory / f'{step.id}.log'
        log_path.write_text(
            f'$ {" ".join(step.command)}\n\nSTDOUT\n{completed_process.stdout}\nSTDERR\n{completed_process.stderr}',
            encoding='utf-8',
        )
        if completed_process.returncode != 0:
            raise WorkflowExecutionError(f'Command exited with code {completed_process.returncode}; see {log_path}')
        if step.output is not None:
            store.write_artifact(step.output, completed_process.stdout)
        return {'command': list(step.command), 'returncode': completed_process.returncode}

    def _execute_parallel(
        self,
        workflow: Workflow,
        step: ParallelStep,
        store: RunStore,
        repository_root: Path,
        state: RunState,
    ) -> dict:
        for child in step.steps:
            self._mark_step_started(state, child.id)
        store.save_state(state)

        results = {}
        failures = {}
        with ThreadPoolExecutor(max_workers=len(step.steps), thread_name_prefix=step.id) as executor:
            futures = {
                executor.submit(self._execute_agent, workflow, child, store, repository_root): child
                for child in step.steps
            }
            for future in as_completed(futures):
                child = futures[future]
                child_record = state.steps[child.id]
                try:
                    result = future.result()
                except Exception as error:
                    child_record['status'] = 'failed'
                    child_record['error'] = str(error)
                    failures[child.id] = str(error)
                else:
                    child_record['status'] = 'succeeded'
                    child_record['metadata'] = result.metadata
                    results[child.id] = result.metadata
                child_record['completed_at'] = _now()

        store.save_state(state)
        if failures:
            failure_summary = '; '.join(f'{child_id}: {message}' for child_id, message in sorted(failures.items()))
            raise WorkflowExecutionError(f'Parallel agents failed: {failure_summary}')
        return {'children': results}

    @staticmethod
    def _render_prompt(step: AgentStep, store: RunStore, repository_root: Path) -> str:
        input_lines = []
        for input_path in step.inputs:
            resolved_path = store.resolve_input(repository_root, input_path)
            input_lines.append(f'- {input_path}: {resolved_path}')
        if not input_lines:
            input_lines.append('- No explicit input artifacts.')

        permission_text = (
            'Do not modify repository files.'
            if step.mode == 'read'
            else 'You may modify files inside the repository when the task requires it.'
        )
        delegation_text = 'Do not spawn subagents.'
        if step.delegation.strategy == 'native':
            delegation_text = (
                f'You may use at most {step.delegation.max_agents} native subagents for independent work. '
                'Wait for every subagent you start, then synthesize their results.'
            )
            if step.delegation.instructions:
                delegation_text += f'\nDelegation instructions: {step.delegation.instructions}'

        schema_text = ''
        if step.schema is not None:
            schema_text = '\nYour final response must conform to the JSON Schema supplied by the runner.'

        return f"""# Workflow stage: {step.id}

This is a fresh workflow context. Use only the repository and the explicit input artifacts listed below.
{permission_text}
{delegation_text}{schema_text}

## Input artifacts

{chr(10).join(input_lines)}

## Task

{step.prompt.strip()}

Return the complete stage artifact in your final response.
The runner captures that response; do not write the artifact path yourself.
"""

    @staticmethod
    def _validated_output(step: AgentStep, output: str) -> str:
        if step.schema is None:
            return output
        try:
            structured_output = json.loads(output)
        except json.JSONDecodeError as error:
            raise WorkflowExecutionError(f'Step {step.id!r} returned invalid JSON: {error}') from error
        try:
            validate(instance=structured_output, schema=step.schema)
        except ValidationError as error:
            raise WorkflowExecutionError(
                f'Step {step.id!r} output does not match its JSON Schema: {error.message}'
            ) from error
        except SchemaError as error:
            raise WorkflowExecutionError(f'Step {step.id!r} has an invalid JSON Schema: {error.message}') from error
        return json.dumps(structured_output, indent=2)

    @staticmethod
    def _mark_step_started(state: RunState, step_id: str) -> None:
        record = state.steps[step_id]
        record['status'] = 'running'
        record['attempts'] += 1
        record['started_at'] = _now()
        record['completed_at'] = None
        record['error'] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
