from core.base_models import BaseModel
from django.db import models
from django.utils.translation import gettext


class Contact(BaseModel):
	class Meta:
		ordering = ('id',)

	class StatusChoices(models.TextChoices):
		ACTIVE = 'ACTIVE', gettext('Active')
		INACTIVE = 'INACTIVE', gettext('Inactive')

	organization = models.ForeignKey('tenancy.Organization', related_name='contacts', null=False, blank=False, verbose_name=gettext('Organization'), on_delete=models.DO_NOTHING)
	email = models.EmailField(unique=True, null=False, blank=False, verbose_name=gettext('Email'))
	first_name = models.TextField(null=False, blank=True, verbose_name=gettext('First Name'))
	last_name = models.TextField(null=False, blank=True, verbose_name=gettext('Last Name'))
	phone = models.TextField(null=False, blank=True, verbose_name=gettext('Phone'))
	status = models.TextField(choices=StatusChoices.choices, default=StatusChoices.ACTIVE, null=False, blank=False, verbose_name=gettext('Status'))
	is_primary = models.BooleanField(default=False, null=False, blank=False, verbose_name=gettext('Is Primary'))
	notes = models.TextField(null=False, blank=True, verbose_name=gettext('Notes'))

	def __str__(self):
		return self.email
