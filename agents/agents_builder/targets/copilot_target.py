from pathlib import Path

from agents.agents_builder.document_types import BuildContext
from agents.agents_builder.file_ops import write_file
from agents.agents_builder.target_assets import render_flat_document
from agents.agents_builder.targets.base_target import BaseTarget


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

        write_file(out_dir / 'AGENTS.md', render_flat_document(context, title='# Agent Guidance'))
        write_file(
            out_dir / '.github' / 'copilot-instructions.md',
            render_flat_document(
                context,
                title='# GitHub Copilot Instructions',
                preamble=preamble,
                example_mode='none',
            ),
        )
