from dataclasses import dataclass, field as dataclass_field
from typing import Any, Optional

from agents.django_codegen.naming import class_case, title_case


FIELD_CLASSES = {
    'text': 'TextField',
    'choice': 'TextField',
    'slug': 'SlugField',
    'email': 'EmailField',
    'url': 'URLField',
    'int': 'IntegerField',
    'positive_int': 'PositiveIntegerField',
    'big_int': 'BigIntegerField',
    'float': 'FloatField',
    'decimal': 'DecimalField',
    'bool': 'BooleanField',
    'date': 'DateField',
    'datetime': 'DateTimeField',
    'time': 'TimeField',
    'duration': 'DurationField',
    'json': 'JSONField',
    'uuid': 'UUIDField',
    'file': 'FileField',
    'image': 'ImageField',
    'fk': 'ForeignKey',
    'o2o': 'OneToOneField',
    'm2m': 'ManyToManyField',
}

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


class SpecError(ValueError):
    """Raised when a resource spec or project profile cannot be understood."""


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

    if kind not in FIELD_CLASSES:
        supported = ', '.join(sorted(FIELD_CLASSES))
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


def render_declaration(field: Field, *, model_name: str, default_on_delete: str, related_name: str) -> str:
    """Render a single model field declaration following the repository argument order."""
    if field.raw:
        return f'{field.name} = {field.raw}'

    field_class = FIELD_CLASSES[field.kind]
    arguments: list[str] = []

    if field.is_relation:
        arguments.append(f"'{field.to}'")
        arguments.append(f"related_name='{field.related_name or related_name}'")

    if field.kind == 'choice':
        choices_class = f'{class_case(field.choices)}Choices'
        arguments.append(f'choices={choices_class}.choices')

    for key in ('max_digits', 'decimal_places', 'max_length'):
        if key in field.extra:
            arguments.append(f'{key}={field.extra[key]}')

    if 'upload_to' in field.extra:
        arguments.append(f"upload_to='{field.extra['upload_to']}'")

    default = render_default(field)
    if default is not None:
        arguments.append(f'default={default}')

    if field.unique:
        arguments.append('unique=True')

    if field.db_index:
        arguments.append('db_index=True')

    if field.kind != 'm2m':
        arguments.append(f'null={field.null}')

    arguments.append(f'blank={field.blank}')
    arguments.append(f"verbose_name=gettext('{field.label}')")

    if field.kind in {'fk', 'o2o'}:
        arguments.append(f'on_delete=models.{field.on_delete or default_on_delete}')

    return f'{field.name} = models.{field_class}({", ".join(arguments)})'


def render_default(field: Field) -> Optional[str]:
    if field.default is None:
        return None

    if field.kind == 'choice':
        choices_class = f'{class_case(field.choices)}Choices'
        return f'{choices_class}.{field.default}'

    if field.kind == 'bool':
        return str(coerce_flag(field.default))

    if field.kind in NUMERIC_KINDS:
        return field.default

    if field.default in {'None', 'dict', 'list'}:
        return field.default

    return f"'{field.default}'"
