import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from agents.django_codegen.naming import (
    class_case,
    kebab_case,
    plural_kebab,
    plural_snake,
    python_tuple,
    snake_case,
    title_case,
)


TEMPLATES_ROOT = Path(__file__).resolve().parent / 'templates'


def build_environment() -> Environment:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATES_ROOT),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    environment.filters['snake'] = snake_case
    environment.filters['kebab'] = kebab_case
    environment.filters['classname'] = class_case
    environment.filters['title_words'] = title_case
    environment.filters['plural_snake'] = plural_snake
    environment.filters['plural_kebab'] = plural_kebab
    environment.filters['py_tuple'] = python_tuple
    environment.globals['render_imports'] = render_imports
    return environment


def render_imports(pairs: list[tuple[str, str]]) -> str:
    """Group (module, name) pairs into sorted, deduplicated import lines."""
    grouped: dict[str, set[str]] = {}

    for module, name in pairs:
        if not module or not name:
            continue

        grouped.setdefault(module, set()).add(name)

    standard: list[str] = []
    local: list[str] = []

    for module, names in sorted(grouped.items()):
        line = f'from {module} import {", ".join(sorted(names))}'
        target = standard if module.split('.')[0] in sys.stdlib_module_names else local
        target.append(line)

    if standard and local:
        return '\n'.join([*standard, '', *local])

    return '\n'.join([*standard, *local])


def apply_indent(text: str, indent: str) -> str:
    """Templates are authored with tabs; convert leading tabs when the profile wants spaces."""
    if indent == '\t':
        return text

    converted: list[str] = []

    for line in text.split('\n'):
        stripped = line.lstrip('\t')
        depth = len(line) - len(stripped)
        converted.append(indent * depth + stripped)

    return '\n'.join(converted)


def render_template(environment: Environment, template_name: str, context: dict, indent: str) -> str:
    template = environment.get_template(template_name)
    rendered = template.render(**context)

    if not rendered.endswith('\n'):
        rendered = f'{rendered}\n'

    return apply_indent(rendered, indent)
