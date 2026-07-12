from pathlib import Path

from agents.agents_builder.document_types import BuildContext
from agents.agents_builder.file_ops import write_file
from agents.agents_builder.target_assets import (
    render_claude_command,
    render_claude_document,
    render_skill_document,
)
from agents.agents_builder.targets.base_target import BaseTarget


class ClaudeTarget(BaseTarget):
    name = 'claude'

    def output_paths(self) -> tuple[str, ...]:
        return ('AGENTS.md', 'CLAUDE.md', '.claude')

    def emit(self, context: BuildContext, out_dir: Path) -> None:
        write_file(out_dir / '.claude' / 'CLAUDE.md', render_claude_document(context))

        for command in context.assets.commands:
            if command.kind != 'command':
                continue

            write_file(out_dir / '.claude' / 'commands' / f'{command.name}.md', render_claude_command(command))

        for skill in context.assets.skills:
            if skill.kind != 'skill':
                continue

            write_file(out_dir / '.claude' / 'skills' / skill.name / 'SKILL.md', render_skill_document(skill))
