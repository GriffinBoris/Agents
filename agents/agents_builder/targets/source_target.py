from pathlib import Path

from ..constants import AGENTS_ROOT
from ..document_types import BuildContext
from ..file_ops import copy_tree
from .base_target import BaseTarget


class SourceTarget(BaseTarget):
    name = 'source'

    def build(self, context: BuildContext, out_dir: Path, *, clean: bool) -> None:  # noqa: ARG002
        self.emit(context, out_dir)

    def emit(self, _context: BuildContext, out_dir: Path) -> None:
        copy_tree(AGENTS_ROOT, out_dir / 'agents')
