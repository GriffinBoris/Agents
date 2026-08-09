import libcst as cst

from agents.rules.python.api import RuleVisitor


class NoDynamicAttributesVisitor(RuleVisitor):
    rule_id = 'AGPY003'
    severity = 'warning'
    message = 'Prefer direct attribute access over dynamic getattr or setattr calls.'

    def visit_Call(self, node: cst.Call) -> None:
        if not isinstance(node.func, cst.Name) or node.func.value not in {'getattr', 'setattr'}:
            return

        if len(node.args) < 2 or isinstance(node.args[1].value, cst.SimpleString):
            return

        self.report(node)
