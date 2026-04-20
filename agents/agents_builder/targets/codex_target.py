from pathlib import Path

from ..document_types import BuildContext
from ..file_ops import write_file
from ..target_assets import render_agents_document, render_skill_document
from .base_target import BaseTarget


class CodexTarget(BaseTarget):
    name = 'codex'

    def output_paths(self) -> tuple[str, ...]:
        return ('AGENTS.md', '.agents')

    def emit(self, context: BuildContext, out_dir: Path) -> None:
        write_file(out_dir / 'AGENTS.md', render_agents_document(context))

        for skill in context.assets.skills:
            if skill.kind != 'skill':
                continue

            write_file(out_dir / '.agents' / 'skills' / skill.name / 'SKILL.md', render_skill_document(skill))
