from pathlib import Path

from ..document_types import BuildContext
from ..file_ops import clean_output_dir, remove_output_path


class BaseTarget:
    name: str

    def output_paths(self) -> tuple[str, ...]:
        raise NotImplementedError

    def build(self, context: BuildContext, out_dir: Path, *, clean: bool) -> None:
        if clean:
            clean_output_dir(out_dir)

        self.emit(context, out_dir)

    def build_in_place(self, context: BuildContext, out_dir: Path, *, clean: bool) -> None:
        if clean:
            for relative_path in self.output_paths():
                remove_output_path(out_dir / relative_path)

        self.emit(context, out_dir)

    def emit(self, context: BuildContext, out_dir: Path) -> None:
        raise NotImplementedError
