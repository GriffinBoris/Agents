from core.base_models import BaseModel
from django.db import models
from django.utils.translation import gettext


class Item(BaseModel):
	history_log_fields = ('status',)

	class Meta:
		ordering = ('sort_order', 'id')
		constraints = (
			models.UniqueConstraint(fields=('catalog_entry', 'code'), name='unique_item_code_per_catalog_entry'),
		)

	class StatusChoices(models.TextChoices):
		ACTIVE = 'ACTIVE', gettext('Active')
		INACTIVE = 'INACTIVE', gettext('Inactive')

	catalog_entry = models.ForeignKey('catalog_entry.CatalogEntry', related_name='items', null=False, blank=False, verbose_name=gettext('Catalog Entry'), on_delete=models.DO_NOTHING)
	name = models.TextField(null=False, blank=False, verbose_name=gettext('Name'))
	code = models.TextField(null=False, blank=False, verbose_name=gettext('Code'))
	status = models.TextField(choices=StatusChoices.choices, default=StatusChoices.ACTIVE, null=False, blank=False, verbose_name=gettext('Status'))
	summary = models.TextField(null=False, blank=True, verbose_name=gettext('Summary'))
	sort_order = models.PositiveIntegerField(default=0, null=False, blank=False, verbose_name=gettext('Sort Order'))

	def __str__(self):
		return self.name
