from dataclasses import dataclass, field as dataclass_field
from typing import Any, Optional

from agents.codegen.errors import SpecError
from agents.codegen.naming import title_case


# Field kinds are described in neutral terms. Each generator maps them to its own
# vocabulary: Django to model field classes, Vue to TypeScript types and zod schemas.
FIELD_KINDS = frozenset(
    {
        'text',
        'choice',
        'slug',
        'email',
        'url',
        'int',
        'positive_int',
        'big_int',
        'float',
        'decimal',
        'bool',
        'date',
        'datetime',
        'time',
        'duration',
        'json',
        'uuid',
        'file',
        'image',
        'fk',
        'o2o',
        'm2m',
    }
)

RELATION_KINDS = frozenset({'fk', 'o2o', 'm2m'})
BOOLEAN_FLAGS = frozenset({'null', 'blank', 'unique', 'db_index', 'editable', 'no_default'})
NUMERIC_KINDS = frozenset({'int', 'positive_int', 'big_int', 'float', 'decimal'})
KNOWN_KEYS = frozenset(
    {
        'type',
        'to',
        'choices',
        'default',
        'related_name',
        'on_delete',
        'verbose_name',
        'max_digits',
        'decimal_places',
        'max_length',
        'upload_to',
        'raw',
        *BOOLEAN_FLAGS,
    }
)


@dataclass(frozen=True)
class Field:
    name: str
    kind: str
    to: Optional[str] = None
    choices: Optional[str] = None
    default: Optional[str] = None
    null: bool = False
    blank: bool = False
    unique: bool = False
    db_index: bool = False
    related_name: Optional[str] = None
    on_delete: Optional[str] = None
    verbose_name: Optional[str] = None
    raw: Optional[str] = None
    no_default: bool = False
    extra: dict[str, str] = dataclass_field(default_factory=dict)

    @property
    def is_relation(self) -> bool:
        return self.kind in RELATION_KINDS

    @property
    def label(self) -> str:
        return self.verbose_name or title_case(self.name)

    @property
    def attname(self) -> str:
        return f'{self.name}_id' if self.is_relation else self.name

    @property
    def target_model(self) -> str:
        if not self.to:
            return ''

        return self.to.split('.')[-1]


def parse_field(name: str, raw_value: Any) -> Field:
    if isinstance(raw_value, str):
        options = parse_field_shorthand(name, raw_value)
    elif isinstance(raw_value, dict):
        options = dict(raw_value)
    else:
        message = f'Field {name} must be a shorthand string or a mapping, got {type(raw_value).__name__}.'
        raise SpecError(message)

    kind = options.pop('type', None)

    if kind is None:
        message = f'Field {name} is missing a type.'
        raise SpecError(message)

    if kind not in FIELD_KINDS:
        supported = ', '.join(sorted(FIELD_KINDS))
        message = f'Field {name} has unsupported type {kind!r}. Supported types: {supported}.'
        raise SpecError(message)

    unknown_keys = set(options) - KNOWN_KEYS
    if unknown_keys:
        message = f'Field {name} has unsupported options: {", ".join(sorted(unknown_keys))}.'
        raise SpecError(message)

    if kind in RELATION_KINDS and not options.get('to'):
        message = f'Field {name} of type {kind} needs a target model such as "fk catalog_entry.CatalogEntry".'
        raise SpecError(message)

    if kind == 'choice' and not options.get('choices'):
        message = f'Field {name} of type choice needs a choices group name.'
        raise SpecError(message)

    if kind == 'decimal' and not (options.get('max_digits') and options.get('decimal_places')):
        message = f'Field {name} of type decimal needs max_digits and decimal_places.'
        raise SpecError(message)

    extra = {key: str(options[key]) for key in ('max_digits', 'decimal_places', 'max_length', 'upload_to') if key in options}

    return Field(
        name=name,
        kind=kind,
        to=options.get('to'),
        choices=options.get('choices'),
        default=None if options.get('default') is None else str(options['default']),
        null=coerce_flag(options.get('null', False)),
        blank=coerce_flag(options.get('blank', False)),
        unique=coerce_flag(options.get('unique', False)),
        db_index=coerce_flag(options.get('db_index', False)),
        related_name=options.get('related_name'),
        on_delete=options.get('on_delete'),
        verbose_name=options.get('verbose_name'),
        raw=options.get('raw'),
        no_default=coerce_flag(options.get('no_default', False)),
        extra=extra,
    )


def parse_field_shorthand(name: str, value: str) -> dict[str, Any]:
    tokens = value.split()

    if not tokens:
        message = f'Field {name} has an empty declaration.'
        raise SpecError(message)

    options: dict[str, Any] = {'type': tokens[0]}
    positional_key = None

    if tokens[0] in RELATION_KINDS:
        positional_key = 'to'
    elif tokens[0] == 'choice':
        positional_key = 'choices'

    for token in tokens[1:]:
        if '=' in token:
            key, _, token_value = token.partition('=')
            options[key] = token_value
            continue

        if positional_key and positional_key not in options:
            options[positional_key] = token
            continue

        options[token] = True

    return options


def coerce_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {'true', 'yes', '1'}


def field_kind_is(field: Field, *kinds: str) -> bool:
    return field.kind in kinds
