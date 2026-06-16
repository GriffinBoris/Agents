#!/usr/bin/env python3

from __future__ import annotations

import argparse
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
GUIDANCE_ROOT = WORKSPACE_ROOT / 'agents' / 'guidance'
DEFAULT_SERVER_URL = 'http://localhost:54321'
DEFAULT_MODEL_ID = 'gpt-5.4'
DEFAULT_PROVIDER_ID = 'github-copilot'
DEFAULT_REASONING_EFFORT = 'high'
GUIDANCE_SETS = {
    'django': ('frameworks', 'django'),
    'python': ('languages', 'python'),
    'view': ('frameworks', 'vue'),
    'vue': ('frameworks', 'vue'),
}

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
class WorkflowOptions:
    model_id: str
    provider_id: str
    mode: str
    reasoning_effort: Optional[str]
    stream: bool


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


class GuidanceReviewWorkflow:
    def __init__(self, client: Opencode, options: WorkflowOptions) -> None:
        self.client = client
        self.options = options

    def run(self, guidance_set: str) -> None:
        documents = collect_guidance_documents(guidance_set)
        print(f'Found {len(documents)} guidance documents for {guidance_set}.')

        for index, document in enumerate(documents, start=1):
            print(f'\n=== Review {index}/{len(documents)}: {relative_path(document)} ===')
            session_id = self.client.session.create().id
            self._run_document_review(session_id, document)

            if index == len(documents):
                return

            if not ask_yes_no('Continue to the next guidance document?', default=True):
                return

    def _run_document_review(self, session_id: str, document: Path) -> None:
        self._run_prompt(session_id, f'/guidance-review {relative_path(document)}')

        while ask_yes_no('Do you need follow-up for this guidance review?', default=False):
            self._run_prompt(session_id, prompt_required('Follow-up prompt'))

    def _run_prompt(self, session_id: str, prompt: str) -> None:
        extra_body = None
        if self.options.reasoning_effort:
            extra_body = {'reasoningEffort': self.options.reasoning_effort}

        print('Running review prompt...')
        reporter = None
        if self.options.stream:
            reporter = StreamReporter(self.client, session_id)
            reporter.start()

        message = self.client.session.chat(
            session_id,
            model_id=self.options.model_id,
            provider_id=self.options.provider_id,
            mode=self.options.mode,
            parts=[{'type': 'text', 'text': prompt}],
            extra_body=extra_body,
        )

        print('Review prompt completed.')
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
        description='Run iterative guidance reviews through OpenCode sessions.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '--guidance-set',
        choices=tuple(sorted(GUIDANCE_SETS)),
        help='Guidance set to review, such as django, vue, view, or python.',
    )
    parser.add_argument(
        '--model',
        default=DEFAULT_MODEL_ID,
        help='Model ID to send to the OpenCode session API.',
    )
    parser.add_argument(
        '--provider',
        default=DEFAULT_PROVIDER_ID,
        help='Provider ID to send to the OpenCode session API.',
    )
    parser.add_argument(
        '--mode',
        default='build',
        help='OpenCode mode to use for the review session. Defaults to build.',
    )
    parser.add_argument(
        '--reasoning-effort',
        choices=('none', 'minimal', 'low', 'medium', 'high', 'xhigh'),
        default=DEFAULT_REASONING_EFFORT,
        help='Optional reasoning effort passthrough for providers that support it.',
    )
    parser.add_argument(
        '--base-url',
        default=DEFAULT_SERVER_URL,
        help='OpenCode server base URL.',
    )
    parser.add_argument(
        '--stream',
        action='store_true',
        help='Print live OpenCode status events while a prompt is running.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    guidance_set = args.guidance_set or prompt_guidance_set()
    api_connection_error = load_opencode_dependency()

    client = Opencode(base_url=args.base_url)
    options = WorkflowOptions(
        model_id=args.model,
        provider_id=args.provider,
        mode=args.mode,
        reasoning_effort=args.reasoning_effort,
        stream=args.stream,
    )

    print(
        'Using OpenCode config: '
        f'base_url={args.base_url} '
        f'provider={options.provider_id} '
        f'model={options.model_id} '
        f'reasoning_effort={options.reasoning_effort} '
        f'mode={options.mode} '
        f'stream={options.stream}'
    )

    try:
        workflow = GuidanceReviewWorkflow(client, options)
        workflow.run(guidance_set)
    except api_connection_error as exc:
        raise SystemExit(
            'Could not connect to the OpenCode server at '
            f'{args.base_url}. '
            'If no server is running, start one first or pass a different `--base-url`. '
            f'Underlying error: {exc}'
        ) from exc

    return 0


def collect_guidance_documents(guidance_set: str) -> list[Path]:
    category, package_name = GUIDANCE_SETS[guidance_set]
    package_root = GUIDANCE_ROOT / category / package_name
    guidance_path = package_root / 'guidance.md'
    examples_root = package_root / 'examples'

    documents = [guidance_path]
    documents.extend(
        path
        for path in sorted(examples_root.glob('*.md'))
        if path.is_file()
    )
    return documents


def relative_path(path: Path) -> str:
    return path.relative_to(WORKSPACE_ROOT).as_posix()


def prompt_guidance_set() -> str:
    choices = ', '.join(sorted(GUIDANCE_SETS))

    while True:
        value = input(f'Guidance set ({choices}): ').strip().lower()
        if value in GUIDANCE_SETS:
            return value

        print('Enter one of the listed guidance sets.')


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
