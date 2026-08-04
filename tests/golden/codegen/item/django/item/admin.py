from django.contrib import admin
from item.models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'catalog_entry',
		'name',
		'code',
		'status',
		'sort_order',
		'created_ts',
		'updated_ts',
	)
	readonly_fields = ('id', 'created_ts', 'updated_ts')
	search_fields = ('name', 'code')
	list_filter = ('status', 'catalog_entry')
	raw_id_fields = ('catalog_entry',)
