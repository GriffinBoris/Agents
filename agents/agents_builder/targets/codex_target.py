from pathlib import Path

from ..constants import DEFAULT_CODEX_CONFIG, TOOLS_ROOT
from ..document_types import BuildContext
from ..file_ops import write_file
from ..target_assets import render_agents_document, render_codex_command_skill, render_skill_document
from .base_target import BaseTarget


class CodexTarget(BaseTarget):
    name = 'codex'

    def output_paths(self) -> tuple[str, ...]:
        return ('AGENTS.md', '.agents', '.codex')

    def emit(self, context: BuildContext, out_dir: Path) -> None:
        write_file(out_dir / '.agents' / 'AGENTS.md', render_agents_document(context))
        write_file(out_dir / '.codex' / 'config.toml', load_codex_config())

        for command in context.assets.commands:
            if command.kind != 'command':
                continue

            write_file(
                out_dir / '.agents' / 'skills' / command.name / 'SKILL.md',
                render_codex_command_skill(command),
            )

        for skill in context.assets.skills:
            if skill.kind != 'skill':
                continue

            write_file(out_dir / '.agents' / 'skills' / skill.name / 'SKILL.md', render_skill_document(skill))


def load_codex_config() -> str:
    config_path = TOOLS_ROOT / 'codex' / 'config.toml'

    if config_path.exists():
        return config_path.read_text(encoding='utf-8')

    return DEFAULT_CODEX_CONFIG
