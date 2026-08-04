import re


CAMEL_BOUNDARY_PATTERN = re.compile(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])')
VOWELS = frozenset('aeiou')


def split_words(value: str) -> list[str]:
    if not value:
        return []

    normalized = value.replace('-', '_')
    parts: list[str] = []

    for chunk in normalized.split('_'):
        if not chunk:
            continue

        if chunk.isupper():
            parts.append(chunk.lower())
            continue

        parts.extend(part.lower() for part in CAMEL_BOUNDARY_PATTERN.split(chunk) if part)

    return parts


def snake_case(value: str) -> str:
    return '_'.join(split_words(value))


def kebab_case(value: str) -> str:
    return '-'.join(split_words(value))


def class_case(value: str) -> str:
    return ''.join(word[:1].upper() + word[1:] for word in split_words(value))


def camel_case(value: str) -> str:
    words = split_words(value)

    if not words:
        return ''

    return words[0] + ''.join(word[:1].upper() + word[1:] for word in words[1:])


def title_case(value: str) -> str:
    return ' '.join(word[:1].upper() + word[1:] for word in split_words(value))


def pluralize(value: str) -> str:
    if not value:
        return value

    lowered = value.lower()

    if lowered.endswith('y') and len(value) > 1 and value[-2].lower() not in VOWELS:
        return f'{value[:-1]}ies'

    if lowered.endswith(('s', 'x', 'z', 'ch', 'sh')):
        return f'{value}es'

    return f'{value}s'


def plural_snake(value: str) -> str:
    return pluralize(snake_case(value))


def plural_kebab(value: str) -> str:
    return kebab_case(plural_snake(value))


def ts_object(entries: list[tuple[str, str]], *, indent: str = '\t', level: int = 1) -> str:
    """Render a TypeScript object literal, one property per line."""
    if not entries:
        return '{}'

    inner_indent = indent * level
    closing_indent = indent * (level - 1)
    lines = [f'{inner_indent}{key}: {value},' for key, value in entries]
    return '{\n' + '\n'.join(lines) + f'\n{closing_indent}}}'


def python_tuple(values: list[str], *, indent: str = '\t', level: int = 2, wrap_at: int = 4) -> str:
    """Render a Python tuple literal, expanding to multiple lines once it grows long."""
    if not values:
        return '()'

    if len(values) == 1:
        return f"('{values[0]}',)"

    single_line = '(' + ', '.join(f"'{value}'" for value in values) + ')'

    if len(values) <= wrap_at and len(single_line) <= 110:
        return single_line

    inner_indent = indent * level
    closing_indent = indent * (level - 1)
    lines = [f"{inner_indent}'{value}'," for value in values]
    return '(\n' + '\n'.join(lines) + f'\n{closing_indent})'
