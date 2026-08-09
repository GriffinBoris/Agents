from agents.rules.python.api import PythonRule
from agents.rules.python.rules.concrete_requests_verb import (
    ConcreteRequestsVerbTransformer,
    ConcreteRequestsVerbVisitor,
)
from agents.rules.python.rules.no_dynamic_attributes import NoDynamicAttributesVisitor
from agents.rules.python.rules.no_future_annotations import NoFutureAnnotationsVisitor

RULES = (
    PythonRule(id='AGPY001', visitor=NoFutureAnnotationsVisitor),
    PythonRule(id='AGPY003', visitor=NoDynamicAttributesVisitor),
    PythonRule(
        id='AGPY005',
        visitor=ConcreteRequestsVerbVisitor,
        transformer=ConcreteRequestsVerbTransformer,
    ),
)

__all__ = ('RULES',)
