from agents.codegen.errors import SpecError
from agents.codegen.generators.base import BaseGenerator, GeneratedFile
from agents.codegen.generators.django.generator import DjangoGenerator
from agents.codegen.generators.vue.generator import VueGenerator


GENERATORS: dict[str, type[BaseGenerator]] = {
    DjangoGenerator.name: DjangoGenerator,
    VueGenerator.name: VueGenerator,
}


def get_generator(name: str) -> BaseGenerator:
    if name not in GENERATORS:
        known = ', '.join(sorted(GENERATORS))
        message = f'Unknown target {name!r}. Known targets: {known}.'
        raise SpecError(message)

    return GENERATORS[name]()


def available_targets() -> tuple[str, ...]:
    return tuple(sorted(GENERATORS))


__all__ = ['BaseGenerator', 'GeneratedFile', 'GENERATORS', 'available_targets', 'get_generator']
