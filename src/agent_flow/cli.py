import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from agent_flow.config import WorkflowConfigError, load_workflow, load_workflow_snapshot
from agent_flow.controller import WorkflowController, WorkflowStateError
from agent_flow.store import RunStore, RunStoreError
from agent_flow.viewer import ViewerError, serve_viewer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='agent-flow',
        description='Maintain file-backed workflows driven by a persistent Codex Desktop parent task.',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    start_parser = subparsers.add_parser('start', help='Create a workflow run without launching agents')
    start_parser.add_argument('workflow', type=Path)
    request_source = start_parser.add_mutually_exclusive_group(required=True)
    request_source.add_argument('--prompt', help='Use inline text as the workflow request')
    request_source.add_argument('--request', type=Path, help='Read the workflow request from a local file')
    request_source.add_argument('--issue', help='Fetch a GitHub issue URL or number with the gh CLI')
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

    view_parser = subparsers.add_parser('view', help='Open the live workflow viewer')
    view_parser.add_argument('run_id', nargs='?', help='Run to select initially; defaults to the most recent run')
    view_parser.add_argument('--repo', type=Path, default=Path.cwd())
    view_parser.add_argument('--port', type=int, default=8765)
    view_parser.add_argument('--no-open', action='store_true', help='Print the URL without opening a browser')

    return parser


def main(arguments: Optional[list[str]] = None) -> int:
    parser = build_parser()
    options = parser.parse_args(arguments)
    controller = WorkflowController()

    try:
        if options.command == 'view':
            serve_viewer(
                options.repo,
                run_id=options.run_id,
                port=options.port,
                open_browser=not options.no_open,
            )
            return 0
        if options.command == 'start':
            workflow = load_workflow(options.workflow)
            if options.issue is not None:
                request_text = _load_github_issue(options.issue, options.repo)
                store, state = controller.start_text(workflow, request_text, options.repo)
            elif options.prompt is not None:
                store, state = controller.start_text(workflow, options.prompt, options.repo)
            else:
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
    except (RunStoreError, ViewerError, WorkflowConfigError, WorkflowStateError) as error:
        sys.stderr.write(f'agent-flow: {error}\n')
        return 1


def _write_json(value: dict) -> None:
    sys.stdout.write(json.dumps(value, indent=2) + '\n')


def _load_github_issue(issue: str, repository_root: Path) -> str:
    try:
        completed = subprocess.run(
            [
                'gh',
                'issue',
                'view',
                issue,
                '--json',
                'number,title,body,url,state,labels,assignees',
            ],
            cwd=repository_root.resolve(),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise RunStoreError('Cannot fetch GitHub issue because the gh CLI is not installed') from error

    if completed.returncode != 0:
        detail = completed.stderr.strip() or 'unknown gh error'
        raise RunStoreError(f'Cannot fetch GitHub issue {issue!r}: {detail}')

    try:
        value = json.loads(completed.stdout)
        number = value['number']
        title = value['title']
        url = value['url']
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise RunStoreError(f'gh returned invalid issue data for {issue!r}') from error

    labels = ', '.join(label['name'] for label in value.get('labels', [])) or 'None'
    assignees = ', '.join(assignee['login'] for assignee in value.get('assignees', [])) or 'None'
    body = value.get('body') or '_No issue body was provided._'
    state = value.get('state', 'UNKNOWN')
    return (
        f'# GitHub Issue #{number}: {title}\n\n'
        f'- Source: {url}\n'
        f'- State: {state}\n'
        f'- Labels: {labels}\n'
        f'- Assignees: {assignees}\n\n'
        f'## Issue body\n\n{body}\n'
    )


if __name__ == '__main__':
    raise SystemExit(main())
