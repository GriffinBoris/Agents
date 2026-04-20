from pathlib import Path
from typing import Any

from .constants import ROOT
from .document_types import GuidancePackage, GuidanceTree, MarkdownDocument


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


def render_shared_guidance(guidance_tree: GuidanceTree, *, example_mode: str) -> str:
    sections: list[str] = []

    if guidance_tree.global_guidance:
        sections.append(guidance_tree.global_guidance.body)

    if guidance_tree.language_packages:
        package_sections = [render_package_section(package, example_mode) for package in guidance_tree.language_packages]
        sections.append('## Languages\n\n' + '\n\n'.join(section for section in package_sections if section))

    if guidance_tree.framework_packages:
        package_sections = [render_package_section(package, example_mode) for package in guidance_tree.framework_packages]
        sections.append('## Frameworks\n\n' + '\n\n'.join(section for section in package_sections if section))

    if guidance_tree.project_package:
        project_section = render_package_section(guidance_tree.project_package, example_mode)
        if project_section:
            sections.append('## Project\n\n' + project_section)

    return '\n\n'.join(section.strip() for section in sections if section.strip()).strip()


def render_package_section(package: GuidancePackage, example_mode: str) -> str:
    sections: list[str] = []

    if package.guidance:
        sections.append(package.guidance.body)

    examples = render_examples(package, example_mode)
    if examples:
        sections.append(examples)

    return '\n\n'.join(section.strip() for section in sections if section.strip()).strip()


def render_examples(package: GuidancePackage, example_mode: str) -> str:
    if not package.examples or example_mode == 'none':
        return ''

    human_name = package.name.replace('_', ' ').replace('-', ' ').title()
    sections = [f'### Examples For {human_name}']

    if example_mode == 'full':
        for example in package.examples:
            sections.append(f'## Example: {example.title}\n\n{example.body}')
    else:
        metadata_lines = [render_example_metadata(example) for example in package.examples]
        sections.append('\n\n'.join(metadata_lines))

    return '\n\n'.join(section.strip() for section in sections if section.strip()).strip()


def render_example_metadata(example: MarkdownDocument) -> str:
    tags = 'None'

    if example.tags:
        tags = ', '.join(f'`{tag}`' for tag in example.tags)

    return '\n'.join(
        [
            f'- path: `{example.path.relative_to(ROOT).as_posix()}`',
            f'  name: `{example.name}`',
            f'  title: {example.title}',
            f'  description: {example.description or "None"}',
            f'  tags: {tags}',
        ]
    )


def render_document(title: str, guidance_tree: GuidanceTree, *, example_mode: str, preamble: str = '') -> str:
    parts = [title.strip()]

    if preamble.strip():
        parts.append(preamble.strip())

    shared_guidance = render_shared_guidance(guidance_tree, example_mode=example_mode)
    if shared_guidance:
        parts.append(shared_guidance)

    return '\n\n'.join(part for part in parts if part).strip() + '\n'
