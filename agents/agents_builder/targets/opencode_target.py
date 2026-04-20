from pathlib import Path

from ..constants import DEFAULT_OPENCODE_JSON, TOOLS_ROOT
from ..document_types import BuildContext
from ..file_ops import write_file
from ..target_assets import render_agents_document, render_opencode_command, render_skill_document, should_emit_command
from .base_target import BaseTarget


class OpenCodeTarget(BaseTarget):
    name = 'opencode'

    def output_paths(self) -> tuple[str, ...]:
        return ('AGENTS.md', 'opencode.json', '.opencode')

    def emit(self, context: BuildContext, out_dir: Path) -> None:
        write_file(out_dir / 'AGENTS.md', render_agents_document(context))
        write_file(out_dir / 'opencode.json', load_opencode_json())

        for command in context.assets.commands:
            if not should_emit_command(command, self.name):
                continue

            write_file(out_dir / '.opencode' / 'commands' / f'{command.name}.md', render_opencode_command(command))

        for skill in context.assets.skills:
            if skill.kind != 'skill':
                continue

            write_file(out_dir / '.opencode' / 'skills' / skill.name / 'SKILL.md', render_skill_document(skill))


def load_opencode_json() -> str:
    opencode_path = TOOLS_ROOT / 'opencode' / 'opencode.json'

    if opencode_path.exists():
        return opencode_path.read_text(encoding='utf-8')

    return DEFAULT_OPENCODE_JSON
