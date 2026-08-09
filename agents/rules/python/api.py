from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

import libcst as cst
from libcst.metadata import CodeRange, PositionProvider


@dataclass(frozen=True)
class Diagnostic:
    rule_id: str
    severity: Literal['error', 'warning']
    message: str
    path: Path
    line: int
    column: int
    fixable: bool

    def format(self) -> str:
        fix_label = ' [fixable]' if self.fixable else ''
        return f'{self.path}:{self.line}:{self.column}: {self.rule_id} {self.severity}: {self.message}{fix_label}'


@dataclass(frozen=True)
class PythonRule:
    id: str
    visitor: type['RuleVisitor']
    transformer: Optional[type[cst.CSTTransformer]] = None

    def __post_init__(self) -> None:
        if self.visitor.rule_id != self.id:
            raise ValueError(f'Rule registration {self.id} does not match visitor {self.visitor.rule_id}.')

        if self.visitor.fixable != (self.transformer is not None):
            raise ValueError(f'Rule {self.id} has inconsistent fixer metadata.')

    @property
    def fixable(self) -> bool:
        return self.transformer is not None


class RuleVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)
    rule_id = ''
    severity: Literal['error', 'warning'] = 'warning'
    message = ''
    fixable = False

    def __init__(self, path: Path, source_lines: tuple[str, ...]) -> None:
        self.path = path
        self.source_lines = source_lines
        self.diagnostics: list[Diagnostic] = []

    def report(self, node: cst.CSTNode, *, message: Optional[str] = None) -> None:
        position = self.get_metadata(PositionProvider, node)
        if self._is_suppressed(position):
            return

        self.diagnostics.append(
            Diagnostic(
                rule_id=self.rule_id,
                severity=self.severity,
                message=message or self.message,
                path=self.path,
                line=position.start.line,
                column=position.start.column + 1,
                fixable=self.fixable,
            )
        )

    def _is_suppressed(self, position: CodeRange) -> bool:
        source_line = self.source_lines[position.start.line - 1]
        agents_directive = f'# agents-lint: ignore {self.rule_id}'
        if agents_directive in source_line:
            return True

        marker = '# noqa'
        if marker not in source_line:
            return False

        suffix = source_line.split(marker, maxsplit=1)[1].strip()
        if not suffix:
            return True

        if not suffix.startswith(':'):
            return False

        codes = {code.strip() for code in suffix[1:].split(',')}
        return self.rule_id in codes
