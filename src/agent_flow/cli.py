import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from agent_flow.config import WorkflowConfigError, load_workflow, load_workflow_snapshot
from agent_flow.controller import WorkflowController, WorkflowStateError
from agent_flow.store import RunStore, RunStoreError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='agent-flow',
        description='Maintain file-backed workflows driven by a persistent Codex Desktop parent task.',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    start_parser = subparsers.add_parser('start', help='Create a workflow run without launching agents')
    start_parser.add_argument('workflow', type=Path)
    start_parser.add_argument('--request', required=True, type=Path)
    start_parser.add_argument('--repo', type=Path, default=Path.cwd())

    for command in ('status', 'approve'):
        command_parser = subparsers.add_parser(command, help=f'{command.capitalize()} a workflow run')
        command_parser.add_argument('run_id')
        command_parser.add_argument('--repo', type=Path, default=Path.cwd())

    for command in ('begin', 'complete', 'shell'):
        command_parser = subparsers.add_parser(command, help=f'{command.capitalize()} a workflow step')
        command_parser.add_argument('run_id')
        command_parser.add_argument('step_id')
        command_parser.add_argument('--repo', type=Path, default=Path.cwd())

    attach_parser = subparsers.add_parser('attach', help='Attach a native worker id to a running step')
    attach_parser.add_argument('run_id')
    attach_parser.add_argument('step_id')
    attach_parser.add_argument('worker_id')
    attach_parser.add_argument('--repo', type=Path, default=Path.cwd())

    fail_parser = subparsers.add_parser('fail', help='Record a failed workflow step')
    fail_parser.add_argument('run_id')
    fail_parser.add_argument('step_id')
    fail_parser.add_argument('--message', required=True)
    fail_parser.add_argument('--repo', type=Path, default=Path.cwd())

    return parser


def main(arguments: Optional[list[str]] = None) -> int:
    parser = build_parser()
    options = parser.parse_args(arguments)
    controller = WorkflowController()

    try:
        if options.command == 'start':
            workflow = load_workflow(options.workflow)
            store, state = controller.start(workflow, options.request, options.repo)
        else:
            store = RunStore.open(options.repo, options.run_id)
            if options.command == 'status':
                state = store.load_state()
            elif options.command == 'approve':
                state = controller.approve(store)
            elif options.command == 'begin':
                state = controller.begin(store, options.step_id)
            elif options.command == 'attach':
                state = controller.attach_worker(store, options.step_id, options.worker_id)
            elif options.command == 'complete':
                state = controller.complete(store, options.step_id)
            elif options.command == 'fail':
                state = controller.fail(store, options.step_id, options.message)
            else:
                state = controller.run_shell(store, options.step_id)

        workflow = load_workflow_snapshot(store.workflow_path)
        _write_json(controller.describe(workflow, store, state))
        return 0
    except (RunStoreError, WorkflowConfigError, WorkflowStateError) as error:
        sys.stderr.write(f'agent-flow: {error}\n')
        return 1


def _write_json(value: dict) -> None:
    sys.stdout.write(json.dumps(value, indent=2) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
