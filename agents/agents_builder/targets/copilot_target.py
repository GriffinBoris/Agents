from pathlib import Path

from ..document_types import BuildContext
from ..file_ops import write_file
from ..guidance_renderer import render_document
from ..target_assets import render_agents_document
from .base_target import BaseTarget


class CopilotTarget(BaseTarget):
    name = 'copilot'

    def output_paths(self) -> tuple[str, ...]:
        return ('AGENTS.md', '.github/copilot-instructions.md')

    def emit(self, context: BuildContext, out_dir: Path) -> None:
        preamble = '\n'.join(
            [
                'Use these repository-wide instructions when generating or modifying code in this project.',
                'Prefer small, explicit changes that follow the existing architecture and conventions.',
                'Verify relevant work before finishing and update guidance when durable patterns change.',
            ]
        )

        write_file(out_dir / 'AGENTS.md', render_agents_document(context))
        write_file(
            out_dir / '.github' / 'copilot-instructions.md',
            render_document(
                '# GitHub Copilot Instructions',
                context.guidance_tree,
                example_mode='none',
                preamble=preamble,
            ),
        )
