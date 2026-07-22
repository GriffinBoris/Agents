from ast import literal_eval
from typing import Optional

import libcst as cst

from agents.rules.python.api import RuleVisitor

HTTP_METHODS = frozenset({'delete', 'get', 'head', 'options', 'patch', 'post', 'put'})


class ConcreteRequestsVerbVisitor(RuleVisitor):
    rule_id = 'AGPY005'
    severity = 'warning'
    message = 'Use a concrete requests verb helper when the HTTP method is already known.'
    fixable = True

    def visit_Call(self, node: cst.Call) -> None:
        match = _concrete_requests_method(node)
        if match is not None:
            method, _ = match
            self.report(node, message=f'Use requests.{method}(...) instead of requests.request(...).')


class ConcreteRequestsVerbTransformer(cst.CSTTransformer):
    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        match = _concrete_requests_method(original_node)
        if match is None or not isinstance(updated_node.func, cst.Attribute):
            return updated_node

        method, method_argument_index = match
        return updated_node.with_changes(
            func=updated_node.func.with_changes(attr=cst.Name(method)),
            args=tuple(argument for index, argument in enumerate(updated_node.args) if index != method_argument_index),
        )


def _concrete_requests_method(node: cst.Call) -> Optional[tuple[str, int]]:
    if not isinstance(node.func, cst.Attribute):
        return None

    if not isinstance(node.func.value, cst.Name) or node.func.value.value != 'requests':
        return None

    if not isinstance(node.func.attr, cst.Name) or node.func.attr.value != 'request':
        return None

    if not node.args:
        return None

    method_argument_index = _method_argument_index(node.args)
    if method_argument_index is None:
        return None

    method_argument = node.args[method_argument_index]
    if not isinstance(method_argument.value, cst.SimpleString):
        return None

    try:
        method = literal_eval(method_argument.value.value).lower()
    except (SyntaxError, ValueError):
        return None

    return (method, method_argument_index) if method in HTTP_METHODS else None


def _method_argument_index(arguments: tuple[cst.Arg, ...]) -> Optional[int]:
    first_argument = arguments[0]
    if first_argument.keyword is None:
        return 0

    for index, argument in enumerate(arguments):
        if isinstance(argument.keyword, cst.Name) and argument.keyword.value == 'method':
            return index

    return None
