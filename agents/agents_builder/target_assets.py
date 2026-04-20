import json
import re

from .document_types import BuildContext, ContentAsset
from .guidance_renderer import render_document


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
    )


def render_claude_document() -> str:
    return render_import_document(
        '# Claude Code Instructions',
        '@../AGENTS.md',
        [
            '## Claude Code',
            '- Project commands live in `.claude/commands/`.',
            '- Project skills live in `.claude/skills/`.',
        ],
    )


def render_gemini_document() -> str:
    return render_import_document(
        '# Gemini CLI Instructions',
        '@AGENTS.md',
        [
            '## Gemini CLI',
            '- Project custom commands live in `.gemini/commands/`.',
            '- Project skills live in `.gemini/skills/`.',
        ],
    )


def render_import_document(title: str, import_path: str, extra_sections: list[str]) -> str:
    parts = [title.strip(), import_path.strip()]

    for section in extra_sections:
        if section.strip():
            parts.append(section.strip())

    return '\n\n'.join(parts).strip() + '\n'


def render_opencode_command(asset: ContentAsset) -> str:
    return render_markdown_command(asset.body, description=asset.description)


def render_claude_command(asset: ContentAsset) -> str:
    return render_markdown_command(convert_claude_arguments(asset.body), description=asset.description)


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
        parts.append('---')
        parts.extend(frontmatter_lines)
        parts.append('---')

    if body.strip():
        parts.append(body.strip())

    return '\n\n'.join(section for section in ('\n'.join(parts[: len(frontmatter_lines) + 2]) if frontmatter_lines else '', body.strip()) if section).strip() + '\n'


def render_yaml_string(key: str, value: str) -> str:
    return f'{key}: {json.dumps(value)}'


def convert_claude_arguments(body: str) -> str:
    def replace(match: re.Match[str]) -> str:
        index = int(match.group(1)) - 1
        return f'${index}' if index >= 0 else match.group(0)

    return re.sub(r'\$(\d+)', replace, body)
