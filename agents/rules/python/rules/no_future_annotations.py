import libcst as cst

from agents.rules.python.api import RuleVisitor


class NoFutureAnnotationsVisitor(RuleVisitor):
    rule_id = 'AGPY001'
    severity = 'error'
    message = 'Do not use from __future__ import annotations.'

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if not isinstance(node.module, cst.Name) or node.module.value != '__future__':
            return

        if isinstance(node.names, cst.ImportStar):
            return

        imports_annotations = any(
            isinstance(alias.name, cst.Name) and alias.name.value == 'annotations' for alias in node.names
        )
        if imports_annotations:
            self.report(node)
