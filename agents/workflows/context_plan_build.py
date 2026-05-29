#!/usr/bin/env python3

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from opencode_ai import APIConnectionError, Opencode
    from opencode_ai.types import StepFinishPart, TextPart
except ModuleNotFoundError as exc:  # pragma: no cover - import guard for local usage
    raise SystemExit(
        'Missing dependency: opencode-ai. Install it with '
        '`python3 -m pip install opencode-ai`. '
        'Then rerun this workflow.'
    ) from exc

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DOCS_ROOT = WORKSPACE_ROOT / 'docs' / 'workflows'
DEFAULT_SERVER_URL = 'http://localhost:54321'
DEFAULT_PROVIDER_ID = 'github-copilot'
DEFAULT_SMALL_MODEL_ID = 'gpt-5-mini'
DEFAULT_BIG_MODEL_ID = 'gpt-5.4'
DEFAULT_SMALL_REASONING_EFFORT = 'low'
DEFAULT_BIG_REASONING_EFFORT = 'high'


@dataclass(frozen=True)
class SessionOptions:
    model_id: str
    provider_id: str
    mode: str
    reasoning_effort: Optional[str]


@dataclass(frozen=True)
class WorkflowArtifacts:
    root: Path
    context_path: Path
    plan_path: Path


class ContextPlanBuildWorkflow:
    def __init__(
        self,
        client: Opencode,
        artifacts: WorkflowArtifacts,
        goal: str,
        scope_text: Optional[str],
        context_options: SessionOptions,
        planning_options: SessionOptions,
        implementation_options: SessionOptions,
    ) -> None:
        self.client = client
        self.artifacts = artifacts
        self.goal = goal
        self.scope_text = scope_text
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
            build_context_prompt(self.goal, self.scope_text, self.artifacts.context_path),
            self.context_options,
            'Context gathering',
        )

    def _run_planning_session(self) -> None:
        print('\n=== Planning Session ===')
        print(describe_options('Planning config', self.planning_options))
        session_id = self.client.session.create().id
        self._run_prompt(
            session_id,
            build_planning_prompt(self.goal, self.scope_text, self.artifacts.context_path, self.artifacts.plan_path),
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
            build_implementation_prompt(self.artifacts.context_path, self.artifacts.plan_path),
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

        message = self.client.session.chat(
            session_id,
            model_id=options.model_id,
            provider_id=options.provider_id,
            mode=options.mode,
            parts=[{'type': 'text', 'text': prompt}],
            extra_body=extra_body,
        )

        print(f'{label} completed.')
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
    client = Opencode(base_url=args.base_url)
    context_options = build_session_options(args, 'context')
    planning_options = build_session_options(args, 'planning')
    implementation_options = build_session_options(args, 'implementation')

    print(f'Workflow scope: {args.scope or "current branch diff against origin/main"}')
    print(describe_options('Context config', context_options))
    print(describe_options('Planning config', planning_options))
    print(describe_options('Implementation config', implementation_options))

    try:
        workflow = ContextPlanBuildWorkflow(
            client=client,
            artifacts=artifacts,
            goal=goal,
            scope_text=args.scope,
            context_options=context_options,
            planning_options=planning_options,
            implementation_options=implementation_options,
        )
        workflow.run()
    except APIConnectionError as exc:
        raise SystemExit(
            'Could not connect to the OpenCode server at '
            f'{args.base_url}. '
            'If no server is running, start one first or pass a different `--base-url`. '
            f'Underlying error: {exc}'
        ) from exc

    return 0


def build_session_options(args: argparse.Namespace, prefix: str) -> SessionOptions:
    return SessionOptions(
        model_id=getattr(args, f'{prefix}_model'),
        provider_id=getattr(args, f'{prefix}_provider'),
        mode=getattr(args, f'{prefix}_mode'),
        reasoning_effort=getattr(args, f'{prefix}_reasoning_effort'),
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


def build_context_prompt(goal: str, scope_text: Optional[str], context_path: Path) -> str:
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


def build_planning_prompt(goal: str, scope_text: Optional[str], context_path: Path, plan_path: Path) -> str:
    scope_line = scope_text or 'current branch diff against origin/main'

    return '\n'.join(
        [
            'Read the dumped context artifact and work with me to create an implementation plan.',
            '',
            f'Goal: {goal}',
            f'Scope: {scope_line}',
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
            '',
            'Work with me interactively:',
            '- ask questions when requirements or tradeoffs are unclear',
            '- revise the plan as I give feedback',
            '- keep the artifact current after every meaningful change',
            '',
            f'In the final response, return the exact written plan artifact path `{relative_path(plan_path)}` and any open questions for me.',
        ]
    )


def build_implementation_prompt(context_path: Path, plan_path: Path) -> str:
    return '\n'.join(
        [
            'Read the implementation plan and execute it in this fresh session.',
            '',
            f'Context artifact: `{relative_path(context_path)}`',
            f'Plan artifact: `{relative_path(plan_path)}`',
            '',
            'Requirements:',
            '- treat the plan artifact as the source of truth',
            '- read the context artifact and any referenced guidance as needed',
            '- implement one focused task at a time',
            '- make the smallest correct changes',
            '- run the smallest relevant verification',
            '- update the plan artifact with execution progress, verification results, and remaining follow-ups',
            '- if a user decision is needed, ask one short question and stop at that boundary',
            '',
            'In the final response:',
            '- summarize the changes made',
            '- list verification run',
            '- list blockers or follow-ups',
            f'- confirm the updated plan artifact path `{relative_path(plan_path)}`',
        ]
    )


def describe_options(label: str, options: SessionOptions) -> str:
    return (
        f'{label}: '
        f'provider={options.provider_id} '
        f'model={options.model_id} '
        f'reasoning_effort={options.reasoning_effort} '
        f'mode={options.mode}'
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
