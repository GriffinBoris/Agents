import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from agent_flow.config import WorkflowConfigError, load_workflow
from agent_flow.runner import WorkflowExecutionError, WorkflowRunner
from agent_flow.store import RunState, RunStore, RunStoreError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='agent-flow', description='Run file-backed Codex and Claude workflows.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser('run', help='Start a workflow run')
    run_parser.add_argument('workflow', type=Path)
    run_parser.add_argument('--request', required=True, type=Path)
    run_parser.add_argument('--repo', type=Path, default=Path.cwd())

    for command in ('approve', 'resume', 'status'):
        command_parser = subparsers.add_parser(command, help=f'{command.capitalize()} a workflow run')
        command_parser.add_argument('run_id')
        command_parser.add_argument('--repo', type=Path, default=Path.cwd())

    return parser


def main(arguments: Optional[list[str]] = None) -> int:
    parser = build_parser()
    options = parser.parse_args(arguments)
    runner = WorkflowRunner()

    try:
        if options.command == 'run':
            workflow = load_workflow(options.workflow)
            store, state = runner.start(workflow, options.request, options.repo)
            _write_state(store, state)
            return 0

        store = RunStore.open(options.repo, options.run_id)
        if options.command == 'approve':
            state = runner.approve(store)
        elif options.command == 'resume':
            state = runner.resume(store)
        else:
            state = store.load_state()
        _write_state(store, state)
        return 0
    except (RunStoreError, WorkflowConfigError, WorkflowExecutionError) as error:
        sys.stderr.write(f'agent-flow: {error}\n')
        return 1


def _write_state(store: RunStore, state: RunState) -> None:
    summary = {
        'run_id': state.run_id,
        'run_directory': str(store.run_directory),
        'status': state.status,
        'waiting_step': state.waiting_step,
        'waiting_message': state.waiting_message,
        'current_step': state.current_step,
    }
    sys.stdout.write(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
