from typing import Optional

from agents.codegen.fields import NUMERIC_KINDS, Field, coerce_flag
from agents.codegen.naming import class_case


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
