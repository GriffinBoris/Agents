from pathlib import Path
from typing import Any

from agents.agents_builder.document_types import GuidancePackage, GuidanceTree


def normalize_body(body: str) -> str:
    cleaned_lines = []

    for line in body.splitlines():
        if line.strip() in {'{% raw %}', '{% endraw %}'}:
            continue

        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines).strip()


def derive_title(path: Path, body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()

        if stripped.startswith('# '):
            return stripped[2:].strip()

    return path.stem.replace('_', ' ').replace('-', ' ').title()


def sort_key(order: Any, path: Path) -> tuple[bool, int, str]:
    return (order is None, 0 if order is None else int(order), path.as_posix())


def shift_headings(body: str, levels: int) -> str:
    if levels <= 0:
        return body

    shifted_lines = []
    inside_fence = False

    for line in body.splitlines():
        if line.lstrip().startswith('```'):
            inside_fence = not inside_fence

        if not inside_fence and line.startswith('#'):
            line = ('#' * levels) + line

        shifted_lines.append(line)

    return '\n'.join(shifted_lines)


def stack_packages(guidance_tree: GuidanceTree) -> list[GuidancePackage]:
    return [*guidance_tree.language_packages, *guidance_tree.framework_packages]


def package_skill_name(package: GuidancePackage) -> str:
    return f'{package.name}-guidance'


def package_description(package: GuidancePackage) -> str:
    if package.guidance and package.guidance.description:
        return package.guidance.description

    return f'Guidance for {package.name}.'


def render_resident_guidance(guidance_tree: GuidanceTree) -> str:
    sections: list[str] = []

    if guidance_tree.global_guidance:
        sections.append(shift_headings(guidance_tree.global_guidance.body, 1))

    stack_index = render_stack_index(guidance_tree)
    if stack_index:
        sections.append(stack_index)

    if guidance_tree.project_package and guidance_tree.project_package.guidance:
        sections.append(shift_headings(guidance_tree.project_package.guidance.body, 1))

    return '\n\n'.join(section.strip() for section in sections if section.strip()).strip()


def render_stack_index(guidance_tree: GuidanceTree) -> str:
    packages = stack_packages(guidance_tree)

    if not packages:
        return ''

    lines = [
        '## Stack Guidance',
        '',
        'Load the matching skill before stack-specific work. Each one carries its own conventions and worked examples.',
        '',
    ]

    for package in packages:
        lines.append(f'- `{package_skill_name(package)}`: {package_description(package)}')

    return '\n'.join(lines)


def render_flat_guidance(guidance_tree: GuidanceTree, *, example_mode: str) -> str:
    sections: list[str] = []

    if guidance_tree.global_guidance:
        sections.append(shift_headings(guidance_tree.global_guidance.body, 1))

    for package in stack_packages(guidance_tree):
        sections.append(render_package_section(package, example_mode))

    if guidance_tree.project_package:
        sections.append(render_package_section(guidance_tree.project_package, example_mode))

    return '\n\n'.join(section.strip() for section in sections if section.strip()).strip()


def render_package_section(package: GuidancePackage, example_mode: str) -> str:
    sections: list[str] = []

    if package.guidance:
        sections.append(shift_headings(package.guidance.body, 1))

    examples = render_examples(package, example_mode)
    if examples:
        sections.append(examples)

    return '\n\n'.join(section.strip() for section in sections if section.strip()).strip()


def render_examples(package: GuidancePackage, example_mode: str) -> str:
    if not package.examples or example_mode != 'full':
        return ''

    sections = ['### Examples']

    for example in package.examples:
        sections.append(shift_headings(example.body, 3))

    return '\n\n'.join(section.strip() for section in sections if section.strip()).strip()


def render_document(title: str, guidance_tree: GuidanceTree, *, example_mode: str, preamble: str = '', flat: bool = False) -> str:
    parts = [title.strip()]

    if preamble.strip():
        parts.append(preamble.strip())

    if flat:
        guidance = render_flat_guidance(guidance_tree, example_mode=example_mode)
    else:
        guidance = render_resident_guidance(guidance_tree)

    if guidance:
        parts.append(guidance)

    return '\n\n'.join(part for part in parts if part).strip() + '\n'
