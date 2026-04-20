from pathlib import Path

from ..document_types import BuildContext
from ..file_ops import write_file
from ..target_assets import (
    render_agents_document,
    render_claude_command,
    render_claude_document,
    render_skill_document,
    should_emit_command,
)
from .base_target import BaseTarget


class ClaudeTarget(BaseTarget):
    name = 'claude'

    def output_paths(self) -> tuple[str, ...]:
        return ('AGENTS.md', '.claude')

    def emit(self, context: BuildContext, out_dir: Path) -> None:
        write_file(out_dir / 'AGENTS.md', render_agents_document(context))
        write_file(out_dir / '.claude' / 'CLAUDE.md', render_claude_document())

        for command in context.assets.commands:
            if not should_emit_command(command, self.name):
                continue

            write_file(out_dir / '.claude' / 'commands' / f'{command.name}.md', render_claude_command(command))

        for skill in context.assets.skills:
            if skill.kind != 'skill':
                continue

            write_file(out_dir / '.claude' / 'skills' / skill.name / 'SKILL.md', render_skill_document(skill))
