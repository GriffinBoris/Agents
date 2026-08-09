AUDIT_FIELDS = ('id', 'created_ts', 'updated_ts')


def missing_admin_audit_fields(
    model_field_names: set[str],
    list_display: tuple[str, ...],
) -> tuple[str, ...]:
    if not set(AUDIT_FIELDS).issubset(model_field_names):
        return ()

    return tuple(field_name for field_name in AUDIT_FIELDS if field_name not in list_display)
