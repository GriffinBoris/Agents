import json
import re
from pathlib import Path

from agents.agents_builder.constants import REFERENCE_ROOT
from agents.agents_builder.document_types import BuildContext, ContentAsset, GuidancePackage
from agents.agents_builder.file_ops import write_file
from agents.agents_builder.frontmatter import parse_frontmatter
from agents.agents_builder.guidance_renderer import (
    package_description,
    package_skill_name,
    render_document,
    stack_packages,
)

REFERENCE_SKILL_NAME = 'guidance-reference'

COMMAND_ROLES = {
    'opencode': 'opencode-command',
    'claude': 'claude-command',
    'copilot': 'copilot-command',
    'codex': 'codex-command',
    'gemini': 'gemini-command',
}


def render_agents_document(context: BuildContext) -> str:
    return render_document(
        '# Agent Guidance',
        context.guidance_tree,
        example_mode=context.example_mode,
        preamble='Stack-specific guidance loads on demand from the skills listed below.',
    )


def render_flat_document(context: BuildContext, *, title: str, preamble: str = '', example_mode: str = '') -> str:
    return render_document(
        title,
        context.guidance_tree,
        example_mode=example_mode or context.example_mode,
        preamble=preamble,
        flat=True,
    )


def render_claude_document(context: BuildContext) -> str:
    return render_document(
        '# Claude Code Guidance',
        context.guidance_tree,
        example_mode=context.example_mode,
        preamble='Project commands live in `.claude/commands/`. Project skills live in `.claude/skills/`.',
    )


def render_gemini_document(context: BuildContext) -> str:
    return render_document(
        '# Gemini CLI Guidance',
        context.guidance_tree,
        example_mode=context.example_mode,
        preamble='Project custom commands live in `.gemini/commands/`. Project skills live in `.gemini/skills/`.',
    )


def emit_guidance_skills(context: BuildContext, skills_dir: Path) -> None:
    for package in stack_packages(context.guidance_tree):
        skill_dir = skills_dir / package_skill_name(package)
        write_file(skill_dir / 'SKILL.md', render_package_skill(package))

        for example in package.examples:
            write_file(skill_dir / 'examples' / example.path.name, example.raw_text)

    emit_reference_skill(skills_dir)


def render_package_skill(package: GuidancePackage) -> str:
    frontmatter = [
        f'name: {package_skill_name(package)}',
        render_yaml_string('description', package_description(package)),
    ]
    sections = []

    if package.guidance:
        sections.append(package.guidance.body)

    if package.examples:
        sections.append(render_example_index(package))

    return render_markdown_with_frontmatter(frontmatter, '\n\n'.join(sections))


def render_example_index(package: GuidancePackage) -> str:
    lines = [
        '## Examples',
        '',
        'Worked examples live beside this file. Read the ones that match the change you are making.',
        '',
    ]

    for example in package.examples:
        summary = example.description or example.title
        lines.append(f'- `examples/{example.path.name}`: {summary}')

    return '\n'.join(lines)


def emit_reference_skill(skills_dir: Path) -> None:
    if not REFERENCE_ROOT.exists():
        return

    reference_paths = sorted(path for path in REFERENCE_ROOT.rglob('*.md') if path.is_file())

    if not reference_paths:
        return

    skill_dir = skills_dir / REFERENCE_SKILL_NAME
    entries = []

    for path in reference_paths:
        relative_path = path.relative_to(REFERENCE_ROOT).as_posix()
        raw_text = path.read_text(encoding='utf-8')
        write_file(skill_dir / relative_path, raw_text)

        frontmatter, _ = parse_frontmatter(raw_text, path)
        summary = frontmatter.get('description') or frontmatter.get('title') or relative_path
        entries.append(f'- `{relative_path}`: {summary}')

    write_file(skill_dir / 'SKILL.md', render_reference_skill(entries))


def render_reference_skill(entries: list[str]) -> str:
    frontmatter = [
        f'name: {REFERENCE_SKILL_NAME}',
        render_yaml_string(
            'description',
            'Review rubric, findings and delta-matrix templates, and the cross-stack anti-pattern catalog. '
            'Load when running a structured review or recording review findings.',
        ),
    ]
    body = '\n'.join(
        [
            '# Guidance Reference',
            '',
            'These reference documents live beside this file. Read the one that matches the task.',
            '',
            *entries,
        ]
    )

    return render_markdown_with_frontmatter(frontmatter, body)


def render_opencode_command(asset: ContentAsset) -> str:
    return render_markdown_command(asset.body, description=asset.description)


def render_claude_command(asset: ContentAsset) -> str:
    return render_markdown_command(asset.body, description=asset.description)


def render_codex_command_skill(asset: ContentAsset) -> str:
    body = convert_codex_command_syntax(asset.body)
    invocation = (
        '## Invocation\n\n'
        'Treat any text supplied with this skill invocation as its arguments. '
        'Follow the argument references in the workflow below.'
    )
    frontmatter = [f'name: {asset.name}']

    if asset.description:
        frontmatter.append(render_yaml_string('description', asset.description))

    return render_markdown_with_frontmatter(frontmatter, f'{invocation}\n\n{body}')


def render_gemini_command(asset: ContentAsset) -> str:
    body = asset.body.replace('$ARGUMENTS', '{{args}}')
    prompt_parts = [
        'Interpret `{{args}}` as the full raw command arguments for this command.',
    ]

    if re.search(r'\$\d+', body):
        prompt_parts.append(
            'If the instructions below mention `$1`, `$2`, or other positional placeholders, '
            'parse them from `{{args}}` in order before acting.'
        )

    prompt_parts.append(body)
    prompt = '\n\n'.join(part.strip() for part in prompt_parts if part.strip())

    lines = []
    if asset.description:
        lines.append(f'description = {json.dumps(asset.description)}')

    lines.append("prompt = '''")
    lines.append(prompt)
    lines.append("'''")

    return '\n'.join(lines).strip() + '\n'


def render_skill_document(asset: ContentAsset) -> str:
    frontmatter = [f'name: {asset.name}']

    if asset.description:
        frontmatter.append(render_yaml_string('description', asset.description))

    return render_markdown_with_frontmatter(frontmatter, asset.body)


def should_emit_command(asset: ContentAsset, target: str) -> bool:
    if asset.kind != 'command':
        return False

    return asset.role in {COMMAND_ROLES[target], 'shared-command'}


def render_markdown_command(body: str, *, description: str) -> str:
    frontmatter = []

    if description:
        frontmatter.append(render_yaml_string('description', description))

    return render_markdown_with_frontmatter(frontmatter, body)


def render_markdown_with_frontmatter(frontmatter_lines: list[str], body: str) -> str:
    parts = []

    if frontmatter_lines:
        parts.append('\n'.join(['---', *frontmatter_lines, '---']))

    if body.strip():
        parts.append(body.strip())

    return '\n\n'.join(parts).strip() + '\n'


def render_yaml_string(key: str, value: str) -> str:
    return f'{key}: {json.dumps(value)}'


def convert_codex_command_syntax(body: str) -> str:
    body = body.replace('$ARGUMENTS', 'the full arguments supplied with this skill')

    def replace_argument(match: re.Match[str]) -> str:
        return f'argument {match.group(1)} supplied with this skill'

    body = re.sub(r'\$(\d+)', replace_argument, body)

    def replace_shell_command(match: re.Match[str]) -> str:
        command = match.group(1).strip()
        return f'Run `{command}` and use its output here.'

    return re.sub(r'^!([^`\n].*)$', replace_shell_command, body, flags=re.MULTILINE)
