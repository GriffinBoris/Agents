from pathlib import Path

from agents.agents_builder.constants import AGENTS_ROOT
from agents.agents_builder.document_types import BuildContext
from agents.agents_builder.file_ops import copy_tree
from agents.agents_builder.targets.base_target import BaseTarget


class SourceTarget(BaseTarget):
    name = 'source'

    def build(self, context: BuildContext, out_dir: Path, *, clean: bool) -> None:  # noqa: ARG002
        self.emit(context, out_dir)

    def emit(self, _context: BuildContext, out_dir: Path) -> None:
        copy_tree(AGENTS_ROOT, out_dir / 'agents')
