#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DOCS_ROOT = WORKSPACE_ROOT / 'docs' / 'workflows'
DEFAULT_SERVER_URL = 'http://localhost:54321'
DEFAULT_PROVIDER_ID = 'github-copilot'
DEFAULT_SMALL_MODEL_ID = 'gpt-5-mini'
DEFAULT_BIG_MODEL_ID = 'gpt-5.4'
DEFAULT_SMALL_REASONING_EFFORT = 'low'
DEFAULT_BIG_REASONING_EFFORT = 'high'

APIConnectionError: type[Exception]
Opencode: object
EventFileEdited: object
EventListResponse: object
EventMessagePartUpdated: object
EventPermissionUpdated: object
EventSessionError: object
EventSessionIdle: object
StepFinishPart: object
StepStartPart: object
TextPart: object
ToolPart: object


def load_opencode_dependency() -> type[Exception]:
    global APIConnectionError
    global Opencode
    global EventFileEdited
    global EventListResponse
    global EventMessagePartUpdated
    global EventPermissionUpdated
    global EventSessionError
    global EventSessionIdle
    global StepFinishPart
    global StepStartPart
    global TextPart
    global ToolPart

    try:
        from opencode_ai import APIConnectionError as loaded_api_connection_error
        from opencode_ai import Opencode as loaded_opencode
        from opencode_ai.types import (
            EventFileEdited as loaded_event_file_edited,
            EventListResponse as loaded_event_list_response,
            EventMessagePartUpdated as loaded_event_message_part_updated,
            EventPermissionUpdated as loaded_event_permission_updated,
            EventSessionError as loaded_event_session_error,
            EventSessionIdle as loaded_event_session_idle,
            StepFinishPart as loaded_step_finish_part,
            StepStartPart as loaded_step_start_part,
            TextPart as loaded_text_part,
            ToolPart as loaded_tool_part,
        )
    except ModuleNotFoundError as exc:  # pragma: no cover - import guard for local usage
        raise SystemExit(
            'Missing dependency: opencode-ai. Install it with '
            '`python3 -m pip install opencode-ai`. '
            'Then rerun this workflow.'
        ) from exc

    APIConnectionError = loaded_api_connection_error
    Opencode = loaded_opencode
    EventFileEdited = loaded_event_file_edited
    EventListResponse = loaded_event_list_response
    EventMessagePartUpdated = loaded_event_message_part_updated
    EventPermissionUpdated = loaded_event_permission_updated
    EventSessionError = loaded_event_session_error
    EventSessionIdle = loaded_event_session_idle
    StepFinishPart = loaded_step_finish_part
    StepStartPart = loaded_step_start_part
    TextPart = loaded_text_part
    ToolPart = loaded_tool_part

    return APIConnectionError


@dataclass(frozen=True)
class SessionOptions:
    model_id: str
    provider_id: str
    mode: str
    reasoning_effort: Optional[str]
    stream: bool


@dataclass(frozen=True)
class WorkflowArtifacts:
    root: Path
    context_path: Path
    plan_path: Path


class StreamReporter:
    def __init__(self, client: Opencode, session_id: str) -> None:
        self.client = client
        self.session_id = session_id
        self.error: Optional[Exception] = None
        self.done = threading.Event()
        self._seen_part_ids: set[str] = set()
        self._seen_permission_ids: set[str] = set()

    def start(self) -> None:
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def wait(self) -> None:
        self.done.wait(timeout=1.0)
        if self.error is not None:
            raise RuntimeError(f'Stream reporter failed: {self.error}')

    def _run(self) -> None:
        event_client = Opencode(base_url=str(self.client.base_url))

        try:
            with event_client.event.list() as stream:
                for event in stream:
                    if self._handle_event(event):
                        return
        except Exception as exc:  # pragma: no cover - best effort status reporting
            self.error = exc
        finally:
            self.done.set()

    def _handle_event(self, event: EventListResponse) -> bool:
        if isinstance(event, EventMessagePartUpdated):
            part = event.properties.part
            if part.session_id != self.session_id or part.id in self._seen_part_ids:
                return False

            self._seen_part_ids.add(part.id)
            self._print_part_status(part)
            return False

        if isinstance(event, EventPermissionUpdated):
            if event.properties.session_id != self.session_id or event.properties.id in self._seen_permission_ids:
                return False

            self._seen_permission_ids.add(event.properties.id)
            print(f'\n[stream] permission requested: {event.properties.title}')
            return False

        if isinstance(event, EventFileEdited):
            print(f'\n[stream] file edited: {event.properties.file}')
            return False

        if isinstance(event, EventSessionError):
            if event.properties.session_id == self.session_id:
                raise RuntimeError(f'Session error: {event.properties.error}')
            return False

        if isinstance(event, EventSessionIdle):
            return event.properties.session_id == self.session_id

        return False

    def _print_part_status(self, part: object) -> None:
        if isinstance(part, TextPart):
            print('\n[stream] assistant text updated')
            return

        if isinstance(part, ToolPart):
            print(f'\n[stream] tool {part.state.status}: {part.tool}')
            return

        if isinstance(part, StepStartPart):
            print('\n[stream] step started')
            return

        if isinstance(part, StepFinishPart):
            print('\n[stream] step finished')


class ContextPlanBuildWorkflow:
    def __init__(
        self,
        client: Opencode,
        artifacts: WorkflowArtifacts,
        goal: str,
        scope_text: Optional[str],
        focus_area: Optional[str],
        create_pr: bool,
        pr_base_branch: Optional[str],
        context_options: SessionOptions,
        planning_options: SessionOptions,
        implementation_options: SessionOptions,
    ) -> None:
        self.client = client
        self.artifacts = artifacts
        self.goal = goal
        self.scope_text = scope_text
        self.focus_area = focus_area
        self.create_pr = create_pr
        self.pr_base_branch = pr_base_branch
        self.context_options = context_options
        self.planning_options = planning_options
        self.implementation_options = implementation_options

    def run(self) -> None:
        self.artifacts.root.mkdir(parents=True, exist_ok=True)

        print(f'Context artifact: {relative_path(self.artifacts.context_path)}')
        print(f'Plan artifact: {relative_path(self.artifacts.plan_path)}')

        self._run_context_session()
        self._run_planning_session()

        if ask_yes_no('Start implementation session now?', default=True):
            self._run_implementation_session()

    def _run_context_session(self) -> None:
        print('\n=== Context Session ===')
        print(describe_options('Context config', self.context_options))
        session_id = self.client.session.create().id
        self._run_prompt(
            session_id,
            build_context_prompt(self.goal, self.scope_text, self.focus_area, self.artifacts.context_path),
            self.context_options,
            'Context gathering',
        )

    def _run_planning_session(self) -> None:
        print('\n=== Planning Session ===')
        print(describe_options('Planning config', self.planning_options))
        session_id = self.client.session.create().id
        self._run_prompt(
            session_id,
            build_planning_prompt(
                self.goal,
                self.scope_text,
                self.focus_area,
                self.create_pr,
                self.pr_base_branch,
                self.artifacts.context_path,
                self.artifacts.plan_path,
            ),
            self.planning_options,
            'Planning',
        )

        while ask_yes_no('Do you want to continue planning or revise the plan?', default=False):
            self._run_prompt(
                session_id,
                prompt_required('Planning follow-up'),
                self.planning_options,
                'Planning follow-up',
            )

    def _run_implementation_session(self) -> None:
        print('\n=== Implementation Session ===')
        print(describe_options('Implementation config', self.implementation_options))
        session_id = self.client.session.create().id
        self._run_prompt(
            session_id,
            build_implementation_prompt(
                self.artifacts.context_path,
                self.artifacts.plan_path,
                self.focus_area,
                self.create_pr,
                self.pr_base_branch,
            ),
            self.implementation_options,
            'Implementation',
        )

        while ask_yes_no('Do you need implementation follow-up?', default=False):
            self._run_prompt(
                session_id,
                prompt_required('Implementation follow-up'),
                self.implementation_options,
                'Implementation follow-up',
            )

    def _run_prompt(self, session_id: str, prompt: str, options: SessionOptions, label: str) -> None:
        extra_body = None
        if options.reasoning_effort:
            extra_body = {'reasoningEffort': options.reasoning_effort}

        print(f'{label} started...')
        reporter = None
        if options.stream:
            reporter = StreamReporter(self.client, session_id)
            reporter.start()

        message = self.client.session.chat(
            session_id,
            model_id=options.model_id,
            provider_id=options.provider_id,
            mode=options.mode,
            parts=[{'type': 'text', 'text': prompt}],
            extra_body=extra_body,
        )

        print(f'{label} completed.')
        if reporter is not None:
            reporter.wait()

        self._print_final_message(session_id, message.id)

        if message.error is not None:
            raise RuntimeError(f'Session error: {message.error}')

    def _print_final_message(self, session_id: str, message_id: str) -> None:
        messages = self.client.session.messages(session_id)

        for item in messages:
            info = item.info
            if info.session_id != session_id or info.id != message_id:
                continue

            step_finish_part = None
            for part in item.parts:
                if isinstance(part, TextPart) and part.text:
                    print(f'\n{part.text.strip()}')

                if isinstance(part, StepFinishPart):
                    step_finish_part = part

            if step_finish_part is not None:
                print(
                    '\n[summary] '
                    f'cost={step_finish_part.cost} '
                    f'input_tokens={step_finish_part.tokens.input} '
                    f'output_tokens={step_finish_part.tokens.output} '
                    f'reasoning_tokens={step_finish_part.tokens.reasoning}'
                )

            print()
            return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Gather context, iterate a plan, and hand it to a fresh implementation session.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--goal', help='What you want this workflow to accomplish.')
    parser.add_argument(
        '--scope',
        help='Explicit scope to investigate. If omitted, the workflow uses the committed current branch diff against origin/main.',
    )
    parser.add_argument(
        '--base-url',
        default=DEFAULT_SERVER_URL,
        help='OpenCode server base URL.',
    )
    parser.add_argument(
        '--stream',
        action='store_true',
        help='Print live OpenCode status events while prompts are running.',
    )
    parser.add_argument(
        '--focus-area',
        help='Extra prompt constraint for the specific area the agents should prioritize.',
    )
    parser.add_argument(
        '--create-pr',
        action='store_true',
        help='Tell the implementation agent to branch from the current branch, commit, push, and open a PR back into it.',
    )

    parser.add_argument('--context-model', default=DEFAULT_SMALL_MODEL_ID, help='Context session model ID.')
    parser.add_argument('--context-provider', default=DEFAULT_PROVIDER_ID, help='Context session provider ID.')
    parser.add_argument('--context-mode', default='build', help='Context session mode.')
    parser.add_argument(
        '--context-reasoning-effort',
        choices=('none', 'minimal', 'low', 'medium', 'high', 'xhigh'),
        default=DEFAULT_SMALL_REASONING_EFFORT,
        help='Context session reasoning effort.',
    )

    parser.add_argument('--planning-model', default=DEFAULT_BIG_MODEL_ID, help='Planning session model ID.')
    parser.add_argument('--planning-provider', default=DEFAULT_PROVIDER_ID, help='Planning session provider ID.')
    parser.add_argument('--planning-mode', default='build', help='Planning session mode.')
    parser.add_argument(
        '--planning-reasoning-effort',
        choices=('none', 'minimal', 'low', 'medium', 'high', 'xhigh'),
        default=DEFAULT_BIG_REASONING_EFFORT,
        help='Planning session reasoning effort.',
    )

    parser.add_argument('--implementation-model', default=DEFAULT_SMALL_MODEL_ID, help='Implementation session model ID.')
    parser.add_argument(
        '--implementation-provider',
        default=DEFAULT_PROVIDER_ID,
        help='Implementation session provider ID.',
    )
    parser.add_argument('--implementation-mode', default='build', help='Implementation session mode.')
    parser.add_argument(
        '--implementation-reasoning-effort',
        choices=('none', 'minimal', 'low', 'medium', 'high', 'xhigh'),
        default=DEFAULT_SMALL_REASONING_EFFORT,
        help='Implementation session reasoning effort.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    goal = args.goal or prompt_required('Goal')
    artifacts = build_artifacts(args.scope)
    pr_base_branch = current_git_branch() if args.create_pr else None
    api_connection_error = load_opencode_dependency()
    client = Opencode(base_url=args.base_url)
    context_options = build_session_options(args, 'context')
    planning_options = build_session_options(args, 'planning')
    implementation_options = build_session_options(args, 'implementation')

    print(f'Workflow scope: {args.scope or "current branch diff against origin/main"}')
    if args.focus_area:
        print(f'Focus area: {args.focus_area}')
    if args.create_pr:
        print(f'PR creation enabled: base_branch={pr_base_branch}')
    print(describe_options('Context config', context_options))
    print(describe_options('Planning config', planning_options))
    print(describe_options('Implementation config', implementation_options))

    try:
        workflow = ContextPlanBuildWorkflow(
            client=client,
            artifacts=artifacts,
            goal=goal,
            scope_text=args.scope,
            focus_area=args.focus_area,
            create_pr=args.create_pr,
            pr_base_branch=pr_base_branch,
            context_options=context_options,
            planning_options=planning_options,
            implementation_options=implementation_options,
        )
        workflow.run()
    except api_connection_error as exc:
        raise SystemExit(
            'Could not connect to the OpenCode server at '
            f'{args.base_url}. '
            'If no server is running, start one first or pass a different `--base-url`. '
            f'Underlying error: {exc}'
        ) from exc

    return 0


def current_git_branch() -> str:
    result = subprocess.run(
        ['git', 'branch', '--show-current'],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    if result.returncode != 0:
        raise SystemExit(f'Could not determine the current git branch: {result.stderr.strip()}')

    branch = result.stdout.strip()
    if not branch:
        raise SystemExit('Could not determine the current git branch. Refusing to create a PR from detached HEAD.')

    return branch


def build_session_options(args: argparse.Namespace, prefix: str) -> SessionOptions:
    return SessionOptions(
        model_id=getattr(args, f'{prefix}_model'),
        provider_id=getattr(args, f'{prefix}_provider'),
        mode=getattr(args, f'{prefix}_mode'),
        reasoning_effort=getattr(args, f'{prefix}_reasoning_effort'),
        stream=args.stream,
    )


def build_artifacts(scope_text: Optional[str]) -> WorkflowArtifacts:
    scope_slug = build_scope_slug(scope_text)
    root = WORKFLOW_DOCS_ROOT / scope_slug
    return WorkflowArtifacts(
        root=root,
        context_path=root / 'context.md',
        plan_path=root / 'implementation-plan.md',
    )


def build_scope_slug(scope_text: Optional[str]) -> str:
    if not scope_text:
        return 'current-branch-diff'

    normalized = []
    previous_was_dash = False

    for char in scope_text.strip().lower():
        if char.isalnum():
            normalized.append(char)
            previous_was_dash = False
            continue

        if previous_was_dash:
            continue

        normalized.append('-')
        previous_was_dash = True

    slug = ''.join(normalized).strip('-')
    return slug or 'scoped-workflow'


def build_context_prompt(goal: str, scope_text: Optional[str], focus_area: Optional[str], context_path: Path) -> str:
    scope_lines = [
        '- scope source: explicit',
        f'- exact scope: {scope_text}',
    ]

    if not scope_text:
        scope_lines = [
            '- scope source: current-branch-diff',
            '- exact scope: git diff origin/main...HEAD',
            '- do not silently mix committed diff scope with dirty working tree changes',
        ]

    return '\n'.join(
        [
            'Gather implementation context and write it to one repeatable artifact.',
            '',
            f'Primary goal: {goal}',
            '',
            *build_focus_section(focus_area),
            'Scope rules:',
            *scope_lines,
            '',
            f'Create or update `{relative_path(context_path)}`.',
            '',
            'Use the context-gatherer mindset:',
            '- build a clear map of the area before drawing conclusions',
            '- show both structure and behavior',
            '- use concrete file paths everywhere',
            '- identify what changed and what remains unchanged or out of scope',
            '',
            'The context artifact must include:',
            '- goal',
            '- scope source',
            '- exact scope text',
            '- changed files, changed areas, or explicit in-scope areas',
            '- unchanged, excluded, or lightly checked areas',
            '- active stacks and concern buckets',
            '- structure inventory with concrete file paths',
            '- key components and responsibilities',
            '- important flows through the scope',
            '- relevant guidance files and examples',
            '- open questions, assumptions, and blind spots',
            '',
            'Do not implement changes in this session.',
            f'In the final response, return the exact written context artifact path `{relative_path(context_path)}`.',
        ]
    )


def build_planning_prompt(
    goal: str,
    scope_text: Optional[str],
    focus_area: Optional[str],
    create_pr: bool,
    pr_base_branch: Optional[str],
    context_path: Path,
    plan_path: Path,
) -> str:
    scope_line = scope_text or 'current branch diff against origin/main'

    return '\n'.join(
        [
            'Read the dumped context artifact and work with me to create an implementation plan.',
            '',
            f'Goal: {goal}',
            f'Scope: {scope_line}',
            *build_focus_section(focus_area),
            f'Context artifact: `{relative_path(context_path)}`',
            f'Plan artifact: `{relative_path(plan_path)}`',
            '',
            f'Create or update `{relative_path(plan_path)}` on every planning turn.',
            '',
            'This plan must be executable by a smaller, faster implementation model in a fresh session.',
            'That means it needs enough context, concrete steps, files, phases, and guidance references that the implementation session can act without rediscovering the whole problem.',
            '',
            'The plan artifact must include:',
            '- goal',
            '- scope',
            '- context artifact path',
            '- in-scope files and areas',
            '- out-of-scope and unchanged areas',
            '- relevant guidance and examples',
            '- assumptions and open questions',
            '- implementation phases',
            '- per-phase tasks with exact files, desired changes, verification, and done criteria',
            '- implementation instructions for the smaller model',
            '- risks, follow-ups, and verification plan',
            *build_planning_pr_section(create_pr, pr_base_branch),
            '',
            'Work with me interactively:',
            '- ask questions when requirements or tradeoffs are unclear',
            '- revise the plan as I give feedback',
            '- keep the artifact current after every meaningful change',
            '',
            f'In the final response, return the exact written plan artifact path `{relative_path(plan_path)}` and any open questions for me.',
        ]
    )


def build_implementation_prompt(
    context_path: Path,
    plan_path: Path,
    focus_area: Optional[str],
    create_pr: bool,
    pr_base_branch: Optional[str],
) -> str:
    return '\n'.join(
        [
            'Read the implementation plan and execute it in this fresh session.',
            '',
            f'Context artifact: `{relative_path(context_path)}`',
            f'Plan artifact: `{relative_path(plan_path)}`',
            '',
            *build_focus_section(focus_area),
            'Requirements:',
            '- treat the plan artifact as the source of truth',
            '- read the context artifact and any referenced guidance as needed',
            '- implement one focused task at a time',
            '- make the smallest correct changes',
            '- run the smallest relevant verification',
            '- update the plan artifact with execution progress, verification results, and remaining follow-ups',
            '- if a user decision is needed, ask one short question and stop at that boundary',
            *build_implementation_pr_section(create_pr, pr_base_branch),
            '',
            'In the final response:',
            '- summarize the changes made',
            '- list verification run',
            '- list blockers or follow-ups',
            f'- confirm the updated plan artifact path `{relative_path(plan_path)}`',
        ]
    )


def build_focus_section(focus_area: Optional[str]) -> list[str]:
    if not focus_area:
        return []

    return [
        'Focus area:',
        f'- prioritize this area: {focus_area}',
        '- use the focus area to narrow attention, but do not ignore direct dependencies or correctness risks',
        '',
    ]


def build_planning_pr_section(create_pr: bool, pr_base_branch: Optional[str]) -> list[str]:
    if not create_pr:
        return []

    return [
        '- PR delivery steps, including feature branch creation, final commit, push, and PR creation',
        f'- PR base branch: `{pr_base_branch}`',
    ]


def build_implementation_pr_section(create_pr: bool, pr_base_branch: Optional[str]) -> list[str]:
    if not create_pr:
        return []

    return [
        '',
        'PR delivery:',
        f'- use `{pr_base_branch}` as the PR base branch',
        '- before implementation changes, create a new feature branch from the PR base branch',
        '- choose a short descriptive branch name for the work',
        '- preserve workflow artifacts that belong to this run, but do not include unrelated dirty changes',
        '- after implementation and verification, inspect `git status --short` and `git diff`',
        '- stage only intended files and create a concise commit',
        '- if commit hooks fail, fix the issues and retry the commit',
        '- push the feature branch to the remote',
        f'- create a pull request with `gh pr create --base {pr_base_branch}`',
        '- include the implementation summary and verification results in the PR body',
        '- if push or PR creation is blocked by auth, network, or permissions, report the exact blocker and leave the branch committed locally',
    ]


def describe_options(label: str, options: SessionOptions) -> str:
    return (
        f'{label}: '
        f'provider={options.provider_id} '
        f'model={options.model_id} '
        f'reasoning_effort={options.reasoning_effort} '
        f'mode={options.mode} '
        f'stream={options.stream}'
    )


def relative_path(path: Path) -> str:
    return path.relative_to(WORKSPACE_ROOT).as_posix()


def prompt_required(label: str) -> str:
    while True:
        value = input(f'{label}: ').strip()
        if value:
            return value

        print(f'{label} is required.')


def ask_yes_no(prompt: str, *, default: bool) -> bool:
    suffix = 'Y/n' if default else 'y/N'

    while True:
        value = input(f'{prompt} [{suffix}]: ').strip().lower()
        if not value:
            return default
        if value in {'y', 'yes'}:
            return True
        if value in {'n', 'no'}:
            return False

        print('Enter yes or no.')


if __name__ == '__main__':
    raise SystemExit(main())
