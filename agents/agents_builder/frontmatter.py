import re
from pathlib import Path
from typing import Any

from .constants import ALLOWED_STATUSES, ROOT, SUPPORTED_FRONTMATTER_FIELDS


def parse_frontmatter(raw_text: str, path: Path) -> tuple[dict[str, Any], str]:
    lines = raw_text.splitlines(keepends=True)

    if not lines or lines[0].strip() != '---':
        return {}, raw_text

    closing_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == '---':
            closing_index = index
            break

    if closing_index is None:
        raise ValueError(f'Frontmatter block is missing a closing --- delimiter in {path.relative_to(ROOT).as_posix()}')

    frontmatter = parse_frontmatter_mapping(lines[1:closing_index], path)
    body = ''.join(lines[closing_index + 1 :])
    return frontmatter, body


def parse_frontmatter_mapping(lines: list[str], path: Path) -> dict[str, Any]:
    frontmatter: dict[str, Any] = {}
    index = 0

    while index < len(lines):
        raw_line = lines[index].rstrip('\n')
        stripped_line = raw_line.strip()

        if not stripped_line:
            index += 1
            continue

        if raw_line.startswith(' '):
            raise ValueError(f'Unsupported nested frontmatter structure in {path.relative_to(ROOT).as_posix()}')

        if ':' not in raw_line:
            raise ValueError(f'Invalid frontmatter line in {path.relative_to(ROOT).as_posix()}: {raw_line}')

        key, raw_value = raw_line.split(':', 1)
        key = key.strip()
        value = raw_value.lstrip()

        if key in frontmatter:
            raise ValueError(f'Duplicate frontmatter field in {path.relative_to(ROOT).as_posix()}: {key}')

        if value in {'>', '|'}:
            block_lines: list[str] = []
            index += 1

            while index < len(lines):
                block_line = lines[index].rstrip('\n')

                if block_line.startswith('  '):
                    block_lines.append(block_line[2:])
                    index += 1
                    continue

                if not block_line.strip():
                    block_lines.append('')
                    index += 1
                    continue

                break

            frontmatter[key] = parse_block_scalar(block_lines, folded=value == '>')
            continue

        if value == '[]':
            frontmatter[key] = []
            index += 1
            continue

        if value == '':
            items: list[str] = []
            next_index = index + 1

            while next_index < len(lines):
                next_line = lines[next_index].rstrip('\n')

                if not next_line.strip():
                    next_index += 1
                    continue

                if next_line.startswith('  - '):
                    items.append(next_line[4:])
                    next_index += 1
                    continue

                if next_line.startswith('  '):
                    raise ValueError(f'Unsupported nested frontmatter structure in {path.relative_to(ROOT).as_posix()}')

                break

            frontmatter[key] = items if items else ''
            index = next_index
            continue

        if re.fullmatch(r'-?\d+', value):
            frontmatter[key] = int(value)
            index += 1
            continue

        frontmatter[key] = value
        index += 1

    return frontmatter


def parse_block_scalar(lines: list[str], *, folded: bool) -> str:
    if not lines:
        return ''

    if not folded:
        return '\n'.join(lines).strip()

    paragraphs: list[str] = []
    current_paragraph: list[str] = []

    for line in lines:
        if line == '':
            if current_paragraph:
                paragraphs.append(' '.join(part.strip() for part in current_paragraph if part.strip()))
                current_paragraph = []

            continue

        current_paragraph.append(line)

    if current_paragraph:
        paragraphs.append(' '.join(part.strip() for part in current_paragraph if part.strip()))

    return '\n\n'.join(paragraphs).strip()


def validate_frontmatter(frontmatter: dict[str, Any], path: Path) -> None:
    for key in frontmatter:
        if key not in SUPPORTED_FRONTMATTER_FIELDS:
            raise ValueError(f'Unsupported frontmatter field in {path.relative_to(ROOT).as_posix()}: {key}')

    status = frontmatter.get('status')
    if status is not None and status not in ALLOWED_STATUSES:
        raise ValueError(f'Unsupported frontmatter status in {path.relative_to(ROOT).as_posix()}: {status}')

    for list_field in ('tags', 'applies_to'):
        value = frontmatter.get(list_field)

        if value is None:
            continue

        if not isinstance(value, list):
            raise ValueError(f'Expected {list_field} to be a list in {path.relative_to(ROOT).as_posix()}')

        if any(not isinstance(item, str) for item in value):
            raise ValueError(f'Expected {list_field} items to be strings in {path.relative_to(ROOT).as_posix()}')

    order = frontmatter.get('order')
    if order is not None and not isinstance(order, int):
        raise ValueError(f'Expected order to be an integer in {path.relative_to(ROOT).as_posix()}')
