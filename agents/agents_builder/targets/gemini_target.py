from pathlib import Path

from ..document_types import BuildContext
from ..file_ops import write_file
from ..target_assets import (
    render_agents_document,
    render_gemini_command,
    render_gemini_document,
    render_skill_document,
    should_emit_command,
)
from .base_target import BaseTarget


class GeminiTarget(BaseTarget):
    name = 'gemini'

    def output_paths(self) -> tuple[str, ...]:
        return ('AGENTS.md', 'GEMINI.md', '.gemini')

    def emit(self, context: BuildContext, out_dir: Path) -> None:
        write_file(out_dir / 'AGENTS.md', render_agents_document(context))
        write_file(out_dir / 'GEMINI.md', render_gemini_document())

        for command in context.assets.commands:
            if not should_emit_command(command, self.name):
                continue

            write_file(out_dir / '.gemini' / 'commands' / f'{command.name}.toml', render_gemini_command(command))

        for skill in context.assets.skills:
            if skill.kind != 'skill':
                continue

            write_file(out_dir / '.gemini' / 'skills' / skill.name / 'SKILL.md', render_skill_document(skill))
