from contact.models import Contact
from django.contrib import admin


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'organization',
		'email',
		'status',
		'is_primary',
		'created_ts',
		'updated_ts',
	)
	readonly_fields = ('id', 'created_ts', 'updated_ts')
	search_fields = ('email', 'first_name', 'last_name')
	list_filter = ('status', 'is_primary', 'organization')
	raw_id_fields = ('organization',)
