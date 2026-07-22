from django.contrib import admin
from django.core.checks import Error, Tags, register

from agents.rules.django_checks.policy import missing_admin_audit_fields


@register(Tags.admin, 'agents')
def check_admin_audit_fields(app_configs, **kwargs):
    del app_configs, kwargs
    errors = []

    for model, model_admin in admin.site._registry.items():
        model_field_names = {field.name for field in model._meta.get_fields()}
        list_display = tuple(model_admin.list_display)
        missing_fields = missing_admin_audit_fields(model_field_names, list_display)
        if not missing_fields:
            continue

        errors.append(
            Error(
                f'AGDJ003: {model._meta.label} admin is missing audit list_display fields: '
                f'{", ".join(missing_fields)}.',
                hint='Add id, created_ts, and updated_ts to list_display.',
                obj=model_admin.__class__,
                id='agents.E003',
            )
        )

    return errors
